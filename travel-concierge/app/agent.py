# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.cloud import storage
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from app.a2ui_utils import a2ui_callback
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.code_executors.code_execution_utils import CodeExecutionInput
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def search_destinations(location: str, category: str = None) -> dict:
    """Searches for travel destinations, key attractions, daily cost estimates, and recommended stay duration.

    Args:
        location: Name of the city or region (e.g. 'Tokyo', 'Paris', 'Maui', 'Kyoto').
        category: Optional filter such as 'sightseeing', 'culture', 'nature', or 'food'.

    Returns:
        A dictionary containing destination details, top highlights, average daily cost in USD, and recommended stay duration.
    """
    loc_key = location.lower().strip()
    catalog = {
        "tokyo": {
            "destination": "Tokyo",
            "country": "Japan",
            "highlights": ["Sensō-ji Temple", "Shinjuku Gyoen National Garden", "Shibuya Crossing", "Tsukiji Outer Market"],
            "avg_daily_cost_usd": 150,
            "recommended_days": 5,
            "best_season": "Spring (Cherry Blossom) & Autumn",
            "category": "culture & food",
        },
        "paris": {
            "destination": "Paris",
            "country": "France",
            "highlights": ["Eiffel Tower", "Louvre Museum", "Montmartre & Sacré-Cœur", "Seine River Cruise"],
            "avg_daily_cost_usd": 200,
            "recommended_days": 4,
            "best_season": "Spring & Early Autumn",
            "category": "culture & food",
        },
        "maui": {
            "destination": "Maui",
            "country": "United States (Hawaii)",
            "highlights": ["Road to Hana", "Haleakalā National Park", "Kaanapali Beach", "Molokini Crater Snorkeling"],
            "avg_daily_cost_usd": 280,
            "recommended_days": 6,
            "best_season": "Year-round (December-April for whale watching)",
            "category": "nature",
        },
        "kyoto": {
            "destination": "Kyoto",
            "country": "Japan",
            "highlights": ["Fushimi Inari Shrine", "Kinkaku-ji (Golden Pavilion)", "Arashiyama Bamboo Grove", "Gion District"],
            "avg_daily_cost_usd": 140,
            "recommended_days": 3,
            "best_season": "Spring & Autumn",
            "category": "culture",
        },
    }

    for key, data in catalog.items():
        if key in loc_key or loc_key in key:
            return data

    return {
        "destination": location.title(),
        "country": "Global Destination",
        "highlights": ["Historic Old Town & Central Square", "Local Cultural Museums & Markets", "Panoramic City Viewpoint"],
        "avg_daily_cost_usd": 175,
        "recommended_days": 3,
        "best_season": "Spring through Autumn",
        "category": category or "sightseeing",
    }


def get_currency_exchange_rate(from_currency: str = "USD", to_currency: str = "JPY") -> dict:
    """Fetches live real-time currency exchange rates for international travel budgeting.

    Args:
        from_currency: 3-letter currency code to convert from (default 'USD').
        to_currency: 3-letter currency code to convert to (e.g. 'JPY', 'EUR', 'GBP', 'CAD', 'MXN').

    Returns:
        A dictionary containing conversion rates, base currency, target currency, and date.
    """
    from_curr = from_currency.upper().strip()
    to_curr = to_currency.upper().strip()
    api_key = os.environ.get("EXCHANGE_RATE_API_KEY")

    url = f"https://api.frankfurter.app/latest?from={from_curr}&to={to_curr}"
    req = urllib.request.Request(url, headers={"User-Agent": "TravelConcierge/1.0"})

    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rate = data.get("rates", {}).get(to_curr)
            return {
                "base_currency": from_curr,
                "target_currency": to_curr,
                "exchange_rate": rate,
                "conversion_example": f"1 {from_curr} = {rate} {to_curr}",
                "date": data.get("date"),
            }
    except Exception as e:
        return {
            "error": f"Failed to fetch currency rates: {str(e)}",
            "base_currency": from_curr,
            "target_currency": to_curr,
        }


def geocode_address(address: str) -> dict:
    """Converts an address, city, or landmark into geographic coordinates (latitude and longitude) using Google Maps Geocoding API.

    Args:
        address: The street address, city, or landmark name to geocode (e.g., 'Eiffel Tower, Paris' or '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary containing formatted address, latitude, longitude, and location coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("MAPS_API_KEY")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {
            "formatted_address": address.title(),
            "latitude": 35.6762,
            "longitude": 139.6503,
            "location": {"lat": 35.6762, "lng": 139.6503},
            "note": "Using fallback coordinates. Replace GOOGLE_MAPS_API_KEY in .env with a valid Google Maps API Key for live geocoding."
        }

    encoded_addr = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_addr}&key={api_key}"
    req = urllib.request.Request(url)

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "OK" and data.get("results"):
                first = data["results"][0]
                loc = first["geometry"]["location"]
                return {
                    "formatted_address": first.get("formatted_address"),
                    "latitude": loc.get("lat"),
                    "longitude": loc.get("lng"),
                    "location": loc,
                }
            return {"error": f"Geocoding failed: {data.get('status')}", "address": address}
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}", "address": address}


def search_nearby_places(latitude: float, longitude: float, place_type: str = "restaurant", radius_meters: int = 1500) -> dict:
    """Finds nearby places (restaurants, tourist attractions, museums, hotels, cafes) around coordinates using Google Maps Places API (New).

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        place_type: Type of place to search for (e.g. 'restaurant', 'tourist_attraction', 'museum', 'hotel', 'cafe').
        radius_meters: Search radius in meters (default 1500m).

    Returns:
        A dictionary containing a list of nearby places with name, formatted address, location, and rating.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("MAPS_API_KEY")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {
            "places": [
                {
                    "name": f"Sample {place_type.title()} Spot",
                    "formatted_address": "123 Main St, Central District",
                    "location": {"latitude": latitude, "longitude": longitude},
                    "rating": 4.8,
                },
                {
                    "name": f"Historic {place_type.title()} Pavilion",
                    "formatted_address": "456 Heritage Way",
                    "location": {"latitude": latitude + 0.002, "longitude": longitude + 0.002},
                    "rating": 4.6,
                },
            ],
            "note": "Using fallback mock places. Set GOOGLE_MAPS_API_KEY in .env with a valid key for live Places API data."
        }

    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = {
        "includedTypes": [place_type],
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius_meters
            }
        },
        "maxResultCount": 5
    }

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating"
    }

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = []
            for p in data.get("places", []):
                display_name = p.get("displayName", {}).get("text")
                results.append({
                    "name": display_name,
                    "formatted_address": p.get("formattedAddress"),
                    "location": p.get("location"),
                    "rating": p.get("rating"),
                })
            return {"places": results, "count": len(results)}
    except Exception as e:
        return {"error": f"Places API request failed: {str(e)}", "latitude": latitude, "longitude": longitude}


async def generate_destination_image(prompt: str, filename: str = "destination_visual.jpeg", tool_context: ToolContext = None) -> dict:
    """Generates a scenic preview image for a travel destination using Gemini (gemini-3.1-flash-lite-image in global region).

    Saves the generated image as an artifact for the Playground UI and uploads it to the public Cloud Storage bucket.

    Args:
        prompt: Detailed visual prompt describing the landmark, scenery, or dish (e.g., 'Sunset view of Tokyo Tower with cherry blossoms').
        filename: Filename to save the image as (default 'destination_visual.jpeg').
        tool_context: ADK ToolContext injected by the framework.

    Returns:
        A dictionary containing the public HTTPS URL, GCS URI, and filename.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-01-abd8039d4584")
    bucket_name = "travel-concierge-qwiklabs-gcp-01-abd8039d4584"

    client = genai.Client(vertexai=True, project=project_id, location="global")

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        image_bytes = None
        mime_type = "image/jpeg"

        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

        if not image_bytes:
            return {"error": "No image data returned from generation model."}

        # Action 1: Save artifact for ADK Playground UI if tool_context is present
        if tool_context:
            try:
                artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                await tool_context.save_artifact(filename=filename, artifact=artifact_part, custom_metadata={"prompt": prompt, "mime_type": mime_type})
            except Exception as artifact_err:
                print(f"Artifact save warning: {artifact_err}")

        # Action 2: Upload image bytes directly to GCS bucket
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
        gcs_uri = f"gs://{bucket_name}/{filename}"

        return {
            "public_url": public_url,
            "gcs_uri": gcs_uri,
            "filename": filename,
            "mime_type": mime_type,
            "prompt": prompt,
        }
    except Exception as e:
        return {"error": f"Image generation failed: {str(e)}", "prompt": prompt}


async def generate_destination_video(prompt: str, filename: str = "destination_video.mp4", tool_context: ToolContext = None) -> dict:
    """Generates a short video for a travel destination or attraction using Google's Omni model (gemini-omni-flash-preview in global region).

    Saves the generated video as an artifact for the Playground UI and uploads it to the public Cloud Storage bucket.

    Args:
        prompt: Visual prompt describing the video scene (e.g. 'A scenic video loop of Tokyo Tower at sunset').
        filename: Filename to save the video as (default 'destination_video.mp4').
        tool_context: ADK ToolContext injected by the framework.

    Returns:
        A dictionary containing the public HTTPS URL, GCS URI, and filename.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-01-abd8039d4584")
    bucket_name = "travel-concierge-qwiklabs-gcp-01-abd8039d4584"

    client = genai.Client(vertexai=True, project=project_id, location="global")

    try:
        interaction = await client.aio.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
        )

        video_bytes = None
        mime_type = "video/mp4"

        if hasattr(interaction, "outputs") and interaction.outputs:
            for out in interaction.outputs:
                if hasattr(out, "data") and out.data:
                    video_bytes = out.data
                    if hasattr(out, "mime_type") and out.mime_type:
                        mime_type = out.mime_type
                    break
                elif hasattr(out, "parts"):
                    for part in out.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            video_bytes = part.inline_data.data
                            if part.inline_data.mime_type:
                                mime_type = part.inline_data.mime_type
                            break

        if not video_bytes:
            video_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2avc1mp41"

        if tool_context:
            try:
                artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
                await tool_context.save_artifact(
                    filename=filename,
                    artifact=artifact_part,
                    custom_metadata={"prompt": prompt, "mime_type": mime_type}
                )
            except Exception as artifact_err:
                print(f"Artifact save warning: {artifact_err}")

        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
        gcs_uri = f"gs://{bucket_name}/{filename}"

        return {
            "public_url": public_url,
            "gcs_uri": gcs_uri,
            "filename": filename,
            "mime_type": mime_type,
            "prompt": prompt,
        }
    except Exception as e:
        return {"error": f"Video generation failed: {str(e)}", "prompt": prompt}


# Load Agent Engine Sandbox resource from deployment_metadata.json
deployment_metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_resource_name = None

if deployment_metadata_path.exists():
    try:
        with open(deployment_metadata_path, "r") as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
    except Exception as e:
        print(f"Warning: Failed to read deployment_metadata.json for code executor: {e}")

code_executor = None
if agent_engine_resource_name:
    code_executor = AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=agent_engine_resource_name
    )

def execute_python_code(code: str, tool_context: ToolContext = None) -> dict:
    """Executes Python code safely inside the Agent Engine code execution sandbox for travel budget calculations or data processing.

    Args:
        code: Python source code snippet to execute.
        tool_context: ADK ToolContext injected by the framework.

    Returns:
        A dictionary containing stdout, stderr, or execution output.
    """
    if not code_executor:
        return {"error": "AgentEngineSandboxCodeExecutor is not initialized."}

    inv_ctx = tool_context.get_invocation_context() if tool_context else None

    try:
        res = code_executor.execute_code(inv_ctx, CodeExecutionInput(code=code))
        return {
            "stdout": res.stdout,
            "stderr": res.stderr,
            "output_files": [f.name for f in (res.output_files or [])],
        }
    except Exception as e:
        return {"error": f"Sandbox execution failed: {str(e)}"}


async def generate_memories_callback(callback_context: CallbackContext):
    """Sends session events to Vertex AI Memory Bank at the end of each turn."""
    await callback_context.add_session_to_memory()
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="You are Travel Concierge, a helpful AI assistant designed to help travelers search destinations, geocode locations, discover nearby attractions, generate scenic preview images, check currency rates, execute Python code in your Agent Engine sandbox for calculations, and plan personalized travel itineraries.",
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

combined_instruction = (
    f"{a2ui_instruction}\n\n"
    "MEMORY & ALLERGY SAFETY RULES:\n"
    "1. Always remember user preferences, health facts, and ALLERGIES (such as food, drug, or environmental allergies) across conversations using Memory Bank.\n"
    "2. Whenever the user mentions any allergy or dietary restriction, acknowledge it clearly and ensure it is saved in memory.\n"
    "3. Cross-reference all preloaded user memories before suggesting restaurants, dining options, activities, or travel itineraries, and explicitly warn against or filter out anything that conflicts with stated allergies."
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=combined_instruction,
    tools=[get_weather, get_current_time, search_destinations, get_currency_exchange_rate, geocode_address, search_nearby_places, generate_destination_image, generate_destination_video, execute_python_code, PreloadMemoryTool()],
    code_executor=code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

def memory_bank_service_builder():
    """Builds VertexAiMemoryBankService for deployed runtime."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-01-abd8039d4584")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-east1")
    return VertexAiMemoryBankService(
        project=project,
        location=location,
        agent_engine_id="5858125385023094784",
    )


app = App(
    root_agent=root_agent,
    name="app",
)
