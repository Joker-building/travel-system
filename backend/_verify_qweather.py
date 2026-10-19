import asyncio
from services.weather_service import WeatherService

async def main():
    svc = WeatherService()
    result = await svc.get_weather_forecast("武汉", days=3)
    print("source:", result.get("source"), "| warning:", result.get("warning"))

if __name__ == "__main__":
    asyncio.run(main())
