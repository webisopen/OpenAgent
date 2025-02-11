import asyncio
import json

import aiohttp
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from openagent.core.io.input import Input, InputMessage

Base = declarative_base()
    
class DataMonitorContent(Base):
    __tablename__ = "data_monitor_snapshot"

    id = Column(Integer, primary_key=True)
    uri = Column(String) # api endpoint
    data = Column(String) # json response
    created_at = Column(DateTime, default=datetime.utcnow)

class DataMonitorApi(BaseModel):
    uri: str
    method: str
    description: str
    polling_interval: int # seconds
    cache_ttl: int # days
    
class DataMonitorConfig(BaseModel):
    apis: list[DataMonitorApi]

class DataMonitorInput(Input[DataMonitorConfig]):
    def __init__(self):
        super().__init__()
        self.apis = []
        self.engine = create_engine("sqlite:///storage/data_monitor.db")
        Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()
        self.next_poll_times: Dict[str, datetime] = {}

    async def setup(self, config: DataMonitorConfig) -> None:
        """Setup data monitor input configuration"""
        self.apis = config.apis

        # Clear expired snapshots
        self.session.query(DataMonitorContent).filter(DataMonitorContent.created_at < datetime.utcnow() - timedelta(days=1)).delete()

        # Set next poll times
        for api in self.apis:
            last_snapshot = self.session.query(DataMonitorContent)\
                .filter(DataMonitorContent.uri == api.uri)\
                .order_by(DataMonitorContent.created_at.desc())\
                .first()
            
            if last_snapshot:
                next_poll = last_snapshot.created_at + timedelta(seconds=api.polling_interval)
            else:
                next_poll = datetime.utcnow()
                
            self.next_poll_times[api.uri] = next_poll

    async def _fetch_api_data(self, api: DataMonitorApi) -> DataMonitorContent:
        """Fetch data from API and store in database"""
        async with aiohttp.ClientSession() as session:
            async with session.request(method=api.method, url=api.uri) as response:
                if response.status != 200:
                    raise Exception(f"API request failed with status {response.status}")
                
                # Get response data
                data = await response.text()
                
                # Create new snapshot
                snapshot = DataMonitorContent(
                    uri=api.uri,
                    data=data,
                    created_at=datetime.utcnow()
                )
                
                # Store in database
                self.session.add(snapshot)
                self.session.commit()
                
                return snapshot

    async def listen(self) -> AsyncIterator[InputMessage]:
        """Listen for data api"""
        while True:
            current_time = datetime.utcnow()
            
            for api in self.apis:
                if current_time >= self.next_poll_times[api.uri]:
                    try:
                        # Fetch and store data
                        data = await self._fetch_api_data(api)
                        
                        # Update next poll time
                        self.next_poll_times[api.uri] = current_time + timedelta(seconds=api.polling_interval)
                        
                        # Filter data based on filters
                        diff_data = self.filter_data(api.uri, data.data)
                        
                        # Update context with relevant information
                        self.context.update({
                            "uri": api.uri,
                            # "description": api.description,
                            "data": diff_data
                        })

                        # Create analysis request message
                        analysis_request = (
                            f"Please analyze the following data changes:\n\n"
                            # f"API Description: {api.description}\n\n"
                            f"Data:\n {diff_data}\n\n"
                        )
                        
                        yield InputMessage(
                            session_id=f"data_monitor_{api.uri}_{current_time.isoformat()}",
                            message=analysis_request
                        )
                        
                    except Exception as e:
                        print(f"Error fetching data from {api.uri}: {str(e)}")
                        # On error, retry after a shorter interval
                        self.next_poll_times[api.uri] = current_time + timedelta(minutes=1)
            
            await asyncio.sleep(1)

    def filter_data(self, uri: str, data: str) -> dict | Any:
        """Filter data based on rules"""
        json_data = json.loads(data)
        
        path = uri.split("/")[-1]
        
        if path == "pool-voter-apy":
            return self.filter_pool_voter_apy(json_data)
        else:
            return json_data
    
    def filter_pool_voter_apy(self, data: dict) -> dict:
        """Filter pool voter apy data"""
        if not data.get('results'):
            return data

        def extract_pool_info(item: dict) -> dict:
            """Extract relevant pool information"""
            root_fields = ('lastEpochChange')
            pool_fields = ('name', 'protocol')

            return {
                **{k: item[k] for k in root_fields},
                **{k: item['pool'][k] for k in pool_fields}
            }

        sorted_results = sorted(
            data['results'],
            key=lambda x: x.get('lastEpochChange', 0),
            reverse=True
        )

        return {
            'top_apy_changes': [extract_pool_info(item) for item in sorted_results[:5]],
            'bottom_apy_changes': [extract_pool_info(item) for item in sorted_results[-5:]] if len(sorted_results) > 5 else [],
            'timestamp': data.get('timestamp'),
            'totalPools': data.get('totalPools')
        }