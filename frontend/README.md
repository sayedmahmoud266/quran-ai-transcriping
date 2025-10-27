# Quran AI Transcription - Frontend

Modern React-based web UI for the Quran AI Transcription service.

## Features

- **Upload Audio Files**: Drag and drop or select audio files for transcription
- **Job Management**: View all jobs with real-time status updates
- **Download Results**: Download transcription results as ZIP files
- **Delete Jobs**: Remove individual jobs or clear all finished jobs
- **Dark Mode**: Beautiful dark theme optimized for readability
- **Real-time Updates**: Auto-refresh job status every 3 seconds

## Tech Stack

- **React 18**: Modern React with hooks
- **Vite**: Fast build tool and dev server
- **TailwindCSS**: Utility-first CSS framework
- **Lucide React**: Beautiful icon library
- **Axios**: HTTP client for API calls

## Development

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

The dev server will start on `http://localhost:5173` with API proxy to `http://localhost:8000`.

### Build for Production

```bash
npm run build
```

This builds the app to `../app/static` directory, which is served by the FastAPI backend.

## Project Structure

```
frontend/
├── src/
│   ├── App.jsx          # Main application component
│   ├── api.js           # API client and endpoints
│   ├── main.jsx         # React entry point
│   └── index.css        # Global styles with Tailwind
├── index.html           # HTML template
├── package.json         # Dependencies
├── vite.config.js       # Vite configuration
├── tailwind.config.js   # Tailwind configuration
└── postcss.config.js    # PostCSS configuration
```

## API Integration

The frontend communicates with the FastAPI backend through the following endpoints:

- `GET /jobs` - List all jobs
- `GET /jobs/{job_id}/status` - Get job status
- `POST /transcribe/async` - Upload audio file
- `GET /jobs/{job_id}/download` - Download result
- `DELETE /jobs/{job_id}` - Delete job
- `DELETE /jobs/finished` - Clear finished jobs
- `GET /health` - Health check

## Building with Makefile

The frontend is automatically built when running:

```bash
make start    # Build frontend and start server
make dev      # Build frontend and start in dev mode
```

Or build manually:

```bash
make build-frontend
```
