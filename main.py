import os
import certifi
from dotenv import load_dotenv
from assistantManager import AssistantManager
from influxdb_client_3 import InfluxDBClient3, flight_client_options


if __name__ == "__main__":
    load_dotenv()

    telegram_bot_token = os.getenv('BOT_TOKEN')
    gemini_token = os.getenv('GEMINI_TOKEN')
    deepgram_token = os.getenv("DEEPGRAM_TOKEN")

    fh = open(certifi.where(), "r")
    cert = fh.read()
    fh.close()
    influxdb_client = InfluxDBClient3(host="https://eu-central-1-1.aws.cloud2.influxdata.com",
                                      token=os.environ.get("INFLUXDB_TOKEN"),
                                      org="UniBo",
                                      flight_client_options=flight_client_options(tls_root_certs=cert))

    assistant = AssistantManager(deepgram_token=deepgram_token,
                                 telegram_bot_token=telegram_bot_token,
                                 gemini_token=gemini_token,
                                 influxdb_client=influxdb_client)
