# Travel Concierge AI Agent

An intelligent, multi-modal AI Travel Concierge built on Google Cloud's **Agent Development Kit (ADK)** and deployed to **Agent Platform (Agent Runtime)**. The agent provides personalized travel planning, real-time weather updates, budget calculations, and multi-modal image and video previews of global destinations.

![Travel Concierge Demo](agent_demo.gif)

---

## Capabilities & Architecture

Travel Concierge combines reasoning capabilities with specialized Google Cloud services and multi-modal generation models:

- **Personalized Itinerary Planning**: Generates day-by-day travel itineraries customized to user preferences, dietary constraints, and travel styles.
- **Cross-Session Memory Bank**: Integrates Vertex AI Memory Bank to retain user preferences (e.g. food allergies, preferred airlines, budget limits) across multiple chat sessions.
- **Multi-Modal Generation**:
  - **Destination Photo Previews**: Generates high-quality photos of attractions using Google's **Imagen 3** (`imagen-3.0-generate-002`).
  - **Video Previews**: Generates short video loops of travel destinations using Google's **Omni Model** (`gemini-omni-flash-preview`).
- **Real-Time Data Retrieval & Math**:
  - Live weather forecasts via Open-Meteo API.
  - Foreign exchange rate conversion via ExchangeRate API.
  - Place discovery and geocoding via Google Maps API.
  - Dynamic budget calculation via Python Code Sandbox Execution.
- **Agent-Driven Rich UI (A2UI)**: Emits structured display UI cards for itineraries, venue lists, and media previews directly in the chat interface.

---

## Integrated Google Cloud Services

- **Vertex AI Agent Engine (Agent Runtime)**: Serverless reasoning engine orchestration supporting A2A (Agent-to-Agent) protocol.
- **Vertex AI Memory Bank**: Managed long-term memory engine for cross-session preference persistence.
- **Google Cloud Storage (GCS)**: Stores generated destination photos and videos in a public bucket.
- **Google Cloud Firestore**: Backend storage for agent state management and memory records.
- **Vertex AI Imagen 3 & Omni Models**: Generative AI models for image and video synthesis.
- **Python Code Execution Sandbox**: Secure code execution environment for financial and mathematical computations.

---

## Local Development & Setup

### Prerequisites

- Python 3.11+
- Google Cloud SDK (`gcloud` authenticated with `roles/aiplatform.user`)
- `agents-cli` v1.1.0+

### Environment Variables

Set the required environment variables:

```bash
export GOOGLE_CLOUD_PROJECT="<your-gcp-project-id>"
export GOOGLE_MAPS_API_KEY="<your-google-maps-api-key>"
export EXCHANGE_RATE_API_KEY="<your-exchangerate-api-key>"
```

### Running the Agent Locally

1. **Install Agent Dependencies**:
   ```bash
   cd travel-concierge
   pip install -r app/requirements.txt
   ```

2. **Test Agent CLI Locally**:
   ```bash
   adk web
   ```

### Running the Custom Chat Frontend

1. **Install Frontend Dependencies**:
   ```bash
   cd frontend
   pip install -r requirements.txt
   ```

2. **Configure & Start Frontend Server**:
   Set `AGENT_ENGINE_RESOURCE_NAME` from your deployment metadata and `AGENT_DIRECTORY="app"`:

   ```bash
   export AGENT_ENGINE_RESOURCE_NAME="projects/<project-id>/locations/us-east1/reasoningEngines/<engine-id>"
   export AGENT_DIRECTORY="app"
   python main.py
   ```
   The local proxy server will start serving traffic on port 8080.

---

## Deployment

### Deploying the Agent to Agent Platform

```bash
agents-cli deploy \
  --project <your-gcp-project-id> \
  --no-confirm-project \
  --update-env-vars GOOGLE_MAPS_API_KEY="$GOOGLE_MAPS_API_KEY",EXCHANGE_RATE_API_KEY="$EXCHANGE_RATE_API_KEY"
```

### Deploying Frontend to Cloud Run

```bash
gcloud run deploy travel-concierge-frontend \
  --source ./frontend \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars="AGENT_ENGINE_RESOURCE_NAME=$AGENT_ENGINE_RESOURCE_NAME,AGENT_DIRECTORY=$AGENT_DIRECTORY"
```
