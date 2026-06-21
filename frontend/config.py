"""Small config helper for the Streamlit frontend (backend URL, defaults)."""

import os

BACKEND_BASE_URL = os.environ.get("PCB_BACKEND_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

RESEARCH_ENDPOINT = f"{BACKEND_BASE_URL}{API_PREFIX}/research"
KB_HEALTH_ENDPOINT = f"{BACKEND_BASE_URL}{API_PREFIX}/kb/health"
KB_INGEST_ENDPOINT = f"{BACKEND_BASE_URL}{API_PREFIX}/kb/ingest"

REQUEST_TIMEOUT_SECONDS = 180  # web scraping can be slow; generous client timeout

EXAMPLE_QUERY = (
    "design a ultra low noise and highly stable current source for 100mA current "
    "range using libbrecht hall design. use ultra precision resistors. include the "
    "power supply for all components and generate all required voltage and "
    "polarities. and use zero drift opamps. the circuit should work from single dc "
    "input. include the required ldos. it should have capability to adjust the "
    "current using a potentiometer. provide me list of components. estimate the "
    "current noise."
)
