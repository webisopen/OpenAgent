import os
import time
import requests
from datetime import datetime, UTC
from typing import Optional, Dict, Any

from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from openagent.agent.config import ModelConfig
from openagent.core.database.engine import create_engine
from openagent.core.tool import Tool

Base = declarative_base()


class PendleStats(Base):
    __tablename__ = "pendle_stats"

    id = Column(Integer, primary_key=True)
    tvl = Column(Float)  # Current TVL in USD
    tvl_change_24h = Column(Float)  # 24h change in USD
    tvl_change_percent = Column(Float)  # 24h change in percent
    volume_7d = Column(Float)  # 7-day volume in USD
    volume_today = Column(Float)  # Today's volume
    volume_prev_day = Column(Float)  # Previous day's volume
    created_at = Column(DateTime, default=datetime.now(UTC))


class PendleDataTrackerConfig(BaseModel):
    """Configuration for data tracking tool"""

    model: Optional[ModelConfig] = Field(
        default=None,
        description="Model configuration for LLM. If not provided, will use agent's core model",
    )


class PendleDataTrackerTool(Tool[PendleDataTrackerConfig]):
    """Tool for tracking Pendle TVL and volume data"""

    def __init__(self, core_model=None):
        super().__init__()
        self.core_model = core_model
        db_url = "sqlite:///" + os.path.join(os.getcwd(), "storage", f"{self.name}.db")
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()

    @property
    def name(self) -> str:
        return "pendle_data_tracker"

    @property
    def description(self) -> str:
        return """
        Tool that tracks Pendle TVL (Total Value Locked) and trading volume.
        """

    async def setup(self, config: PendleDataTrackerConfig) -> None:
        """Setup the tracking tool"""
        pass

    async def __call__(self) -> str:
        """
        Track Pendle data and return a structured report

        Returns:
            str: Formatted report of Pendle statistics
        """
        logger.info(f"{self.name} tool is called.")

        try:
            # Get current Pendle data
            tracker = PendleTracker()
            data = tracker.get_pendle_data()

            if not data:
                return "Error: Unable to fetch Pendle data"

            # Parse the data for storage
            try:
                tvl_value = float(data["Latest TVL"].split("$")[1].split("B")[0]) * 1e9
                tvl_change_parts = data["TVL 24h Change"].split("$")[1].split("M")[0]
                tvl_change_24h = float(tvl_change_parts) * 1e6
                tvl_change_percent = float(
                    data["TVL 24h Change"].split("(")[1].split("%")[0]
                )
                volume_7d = (
                    float(data["Total 7d Volume"].split("$")[1].split("B")[0]) * 1e9
                )
                volume_today = (
                    float(data["Today's Volume"].split("$")[1].split("M")[0]) * 1e6
                )
                volume_prev = (
                    float(data["Previous Day's Volume"].split("$")[1].split("M")[0])
                    * 1e6
                )
            except Exception as e:
                logger.error(f"Error parsing data values: {e}")
                return f"Error parsing data: {str(e)}"

            # Create and store the new stats
            stats = PendleStats(
                tvl=tvl_value,
                tvl_change_24h=tvl_change_24h,
                tvl_change_percent=tvl_change_percent,
                volume_7d=volume_7d,
                volume_today=volume_today,
                volume_prev_day=volume_prev,
                created_at=datetime.now(UTC),
            )

            # Check if TVL increased
            if tvl_change_percent <= 0:
                return "TVL has not increased, no tweet needed."

            # Store the data
            self.session.add(stats)
            self.session.commit()

            # Format response - directly use the readable format from PendleTracker
            formatted_response = f"""
=== Pendle Data Statistics ===
Latest TVL: {data["Latest TVL"]}
TVL 24h Change: {data["TVL 24h Change"]}
Total 7d Volume: {data["Total 7d Volume"]}
Today's Volume: {data["Today's Volume"]}
Previous Day's Volume: {data["Previous Day's Volume"]}
Statistics time: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""

            logger.info(f"{self.name} tool response: {formatted_response.strip()}.")
            return formatted_response.strip()

        except Exception as e:
            error_msg = f"Error tracking data: {e}"
            logger.error(error_msg)
            return error_msg


class PendleTracker:
    def __init__(self):
        self.sentio_base_url = (
            "https://app.sentio.xyz/api/v1/insights/pendle/pendle-internal/query"
        )
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": "https://app.sentio.xyz",
            "Referer": "https://app.sentio.xyz/share/lv18u9fyu1b558xf?from=now-7d&to=now",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "share-dashboard": "lv18u9fyu1b558xf/-RhF6YBxZRH7oqoK",
        }
        self.proxies = {"http": None, "https": None}
        self.results = {}

    def get_pendle_data(self) -> Dict[str, Any]:
        """Fetch Pendle TVL and trading volume data"""
        # TVL request payload
        tvl_payload = {
            "projectOwner": "pendle",
            "projectSlug": "pendle-internal",
            "timeRange": {
                "start": "now-7d",
                "end": "now",
                "step": 86400,
                "timezone": "Asia/Shanghai",
            },
            "limit": 20,
            "queries": [
                {
                    "metricsQuery": {
                        "query": "overall_tvl",
                        "alias": "TVL",
                        "id": "a",
                        "labelSelector": {},
                        "aggregate": {"op": "SUM", "grouping": []},
                        "functions": [],
                        "color": "",
                        "disabled": False,
                    },
                    "dataSource": "METRICS",
                    "sourceName": "",
                }
            ],
            "formulas": [],
            "cachePolicy": {
                "noCache": False,
                "cacheTtlSecs": 302400,
                "cacheRefreshTtlSecs": 43200,
            },
            "share-dashboard": "lv18u9fyu1b558xf/-RhF6YBxZRH7oqoK",
        }

        # Trading volume request payload
        volume_payload = {
            "projectOwner": "pendle",
            "projectSlug": "pendle-internal",
            "timeRange": {
                "start": "now-7d",
                "end": "now",
                "step": 86400,
                "timezone": "Asia/Shanghai",
            },
            "limit": 20,
            "queries": [
                {
                    "metricsQuery": {
                        "query": "trading_volume",
                        "alias": "",
                        "id": "a",
                        "labelSelector": {},
                        "aggregate": {"op": "SUM", "grouping": []},
                        "functions": [
                            {
                                "name": "rollup_delta",
                                "arguments": [
                                    {"durationValue": {"value": 1, "unit": "d"}}
                                ],
                            }
                        ],
                        "color": "",
                        "disabled": False,
                    },
                    "dataSource": "METRICS",
                    "sourceName": "",
                }
            ],
            "formulas": [],
            "cachePolicy": {
                "noCache": False,
                "cacheTtlSecs": 302400,
                "cacheRefreshTtlSecs": 43200,
            },
        }

        try:
            max_retries = 3
            retry_interval = 5
            tvl_data = {}
            volume_data = {}
            tvl_success = False

            # Fetch TVL data
            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"Attempting to fetch TVL data (attempt {attempt + 1}/{max_retries})..."
                    )
                    tvl_headers = self.headers.copy()
                    response = requests.post(
                        self.sentio_base_url,
                        headers=tvl_headers,
                        json=tvl_payload,
                        proxies=self.proxies,
                        verify=False,
                        timeout=10,
                    )
                    response.raise_for_status()
                    tvl_data = response.json()
                    logger.success("Successfully fetched TVL data!")
                    tvl_success = True
                    break
                except Exception as e:
                    logger.error(
                        f"Error fetching TVL data (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        logger.info(
                            f"Waiting {retry_interval} seconds before retrying..."
                        )
                        time.sleep(retry_interval)
                    else:
                        logger.warning("Maximum retry attempts reached")

            # Fetch trading volume data with three retry attempts
            volume_success = False
            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"Attempting to fetch trading volume data (attempt {attempt + 1}/{max_retries})..."
                    )
                    # Create new headers for volume request with different share-dashboard
                    volume_headers = self.headers.copy()
                    volume_headers["share-dashboard"] = (
                        "lv18u9fyu1b558xf/xFlnOyRuQR8tigTd"
                    )

                    response = requests.post(
                        self.sentio_base_url,
                        headers=volume_headers,
                        json=volume_payload,
                        proxies=self.proxies,
                        verify=False,
                        timeout=10,
                    )
                    response.raise_for_status()
                    volume_data = response.json()
                    logger.success("Successfully fetched trading volume data!")
                    volume_success = True
                    break
                except Exception as e:
                    logger.error(
                        f"Error fetching trading volume data (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    if hasattr(e, "response"):
                        logger.debug(f"Response status code: {e.response.status_code}")
                        logger.debug(f"Response content: {e.response.text}")
                    if attempt < max_retries - 1:
                        logger.info(
                            f"Waiting {retry_interval} seconds before retrying..."
                        )
                        time.sleep(retry_interval)
                    else:
                        logger.warning("Maximum retry attempts reached")
                        logger.warning(
                            "Unable to fetch trading volume data, processing TVL data only"
                        )

            # Parse data
            if tvl_success and tvl_data:
                try:
                    self._parse_tvl_data(tvl_data)
                except Exception as e:
                    logger.error(f"Error parsing TVL data: {e}")

            if volume_success and volume_data:
                try:
                    self._parse_volume_data(volume_data)
                except Exception as e:
                    logger.error(f"Error parsing trading volume data: {e}")

            if not tvl_success and not volume_success:
                logger.error(
                    "Unable to fetch any data, please check network connection or API availability"
                )
                return {}

            return self.results

        except Exception as e:
            logger.exception(f"Error fetching Pendle data: {e}")
            return {}

    def _parse_tvl_data(self, data):
        """Parse TVL data"""
        results = data.get("results", [])
        tvl_data = next((result for result in results if result["id"] == "a"), None)
        if tvl_data and tvl_data["matrix"]["samples"]:
            tvl_values = tvl_data["matrix"]["samples"][0]["values"]

            # Get latest data
            latest_tvl = tvl_values[-1]["value"]
            latest_time = datetime.fromtimestamp(int(tvl_values[-1]["timestamp"]))

            # Get previous data point
            day_ago_index = max(0, len(tvl_values) - 2)  # Index for previous day
            day_ago_tvl = (
                tvl_values[day_ago_index]["value"] if day_ago_index >= 0 else 0
            )

            # Calculate changes
            tvl_change = latest_tvl - day_ago_tvl
            tvl_change_percent = (
                (tvl_change / day_ago_tvl * 100) if day_ago_tvl > 0 else 0
            )

            # Format results
            self.results["Latest TVL"] = (
                f"${latest_tvl / 1e9:.2f}B ({latest_time.strftime('%Y-%m-%d %H:%M')})"
            )
            self.results["TVL 24h Change"] = (
                f"${tvl_change / 1e6:.2f}M ({tvl_change_percent:.2f}%)"
            )

            # Process daily data
            for i, data_point in enumerate(tvl_values):
                timestamp = datetime.fromtimestamp(int(data_point["timestamp"]))
                date_str = timestamp.strftime("%Y-%m-%d")
                self.results[f"TVL on {date_str}"] = (
                    f"${data_point['value'] / 1e9:.2f}B"
                )

    def _parse_volume_data(self, data):
        """Parse trading volume data"""
        results = data.get("results", [])
        volume_data = next((result for result in results if result["id"] == "a"), None)
        if volume_data and volume_data["matrix"]["samples"]:
            volume_values = volume_data["matrix"]["samples"][0]["values"]

            # Get latest data (today)
            latest_volume = volume_values[-1]["value"] if len(volume_values) > 0 else 0
            latest_time = (
                datetime.fromtimestamp(int(volume_values[-1]["timestamp"]))
                if len(volume_values) > 0
                else datetime.now()
            )

            # Get previous day data
            prev_day_volume = (
                volume_values[-2]["value"] if len(volume_values) > 1 else 0
            )
            prev_day_time = (
                datetime.fromtimestamp(int(volume_values[-2]["timestamp"]))
                if len(volume_values) > 1
                else datetime.now()
            )

            # Process daily data
            for i, data_point in enumerate(volume_values):
                timestamp = datetime.fromtimestamp(int(data_point["timestamp"]))
                date_str = timestamp.strftime("%Y-%m-%d")
                self.results[f"Volume on {date_str}"] = (
                    f"${data_point['value'] / 1e6:.2f}M"
                )

            # Calculate total volume
            total_volume = sum(data_point["value"] for data_point in volume_values)

            # Update results
            self.results["Total 7d Volume"] = f"${total_volume / 1e9:.2f}B"
            self.results["Today's Volume"] = (
                f"${latest_volume / 1e6:.2f}M ({latest_time.strftime('%Y-%m-%d')})"
            )
            self.results["Previous Day's Volume"] = (
                f"${prev_day_volume / 1e6:.2f}M ({prev_day_time.strftime('%Y-%m-%d')})"
            )
