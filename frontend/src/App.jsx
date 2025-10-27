import { useState, useEffect, useCallback } from 'react';
import { 
  Upload, 
  RefreshCw, 
  Download, 
  Trash2, 
  FileAudio, 
  Clock, 
  CheckCircle, 
  XCircle, 
  Loader,
  AlertCircle,
  Activity
} from 'lucide-react';
import { jobsApi } from './api';

function App() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');
  const [health, setHealth] = useState(null);

  // Fetch jobs
  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      const statusFilter = filterStatus === 'all' ? null : filterStatus;
      const data = await jobsApi.getAllJobs(statusFilter);
      setJobs(data.jobs || []);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  // Fetch health status
  const fetchHealth = async () => {
    try {
      const data = await jobsApi.healthCheck();
      setHealth(data);
    } catch (error) {
      console.error('Error fetching health:', error);
    }
  };

  // Initial load and polling
  useEffect(() => {
    fetchJobs();
    fetchHealth();
    
    const jobInterval = setInterval(fetchJobs, 3000); // Poll every 3 seconds
    const healthInterval = setInterval(fetchHealth, 5000); // Poll every 5 seconds
    
    return () => {
      clearInterval(jobInterval);
      clearInterval(healthInterval);
    };
  }, [fetchJobs]);

  // Handle file selection
  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  // Handle file upload
  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      setUploadProgress(0);
      
      await jobsApi.uploadAudio(selectedFile, (progress) => {
        setUploadProgress(progress);
      });

      setSelectedFile(null);
      setUploadProgress(0);
      fetchJobs();
      
      // Reset file input
      const fileInput = document.getElementById('file-input');
      if (fileInput) fileInput.value = '';
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Failed to upload file: ' + error.message);
    } finally {
      setUploading(false);
    }
  };

  // Handle download
  const handleDownload = async (jobId, originalFilename) => {
    try {
      const filename = originalFilename 
        ? `${originalFilename.split('.')[0]}_trs_${jobId}.zip`
        : `result_${jobId}.zip`;
      await jobsApi.downloadResult(jobId, filename);
    } catch (error) {
      console.error('Error downloading result:', error);
      alert('Failed to download result: ' + error.message);
    }
  };

  // Handle delete
  const handleDelete = async (jobId) => {
    if (!confirm('Are you sure you want to delete this job?')) return;

    try {
      await jobsApi.deleteJob(jobId);
      fetchJobs();
    } catch (error) {
      console.error('Error deleting job:', error);
      alert('Failed to delete job: ' + error.message);
    }
  };

  // Handle clear finished
  const handleClearFinished = async () => {
    if (!confirm('Are you sure you want to clear all finished jobs?')) return;

    try {
      const result = await jobsApi.clearFinishedJobs();
      alert(`Deleted ${result.deleted_count} finished jobs`);
      fetchJobs();
    } catch (error) {
      console.error('Error clearing finished jobs:', error);
      alert('Failed to clear finished jobs: ' + error.message);
    }
  };

  // Get status badge
  const getStatusBadge = (status) => {
    const badges = {
      queued: { icon: Clock, color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
      processing: { icon: Loader, color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
      completed: { icon: CheckCircle, color: 'bg-green-500/20 text-green-400 border-green-500/30' },
      failed: { icon: XCircle, color: 'bg-red-500/20 text-red-400 border-red-500/30' },
    };

    const badge = badges[status] || badges.queued;
    const Icon = badge.icon;

    return (
      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${badge.color}`}>
        <Icon className={`w-3.5 h-3.5 ${status === 'processing' ? 'animate-spin' : ''}`} />
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  // Format date
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">Quran AI Transcription</h1>
              <p className="mt-1 text-sm text-gray-400">Verse-level audio transcription service</p>
            </div>
            
            {/* Health Status */}
            {health && (
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-green-400" />
                  <span className="text-gray-300">
                    Worker: <span className="text-green-400 font-medium">
                      {health.worker_running ? 'Running' : 'Stopped'}
                    </span>
                  </span>
                </div>
                <div className="text-gray-300">
                  Queue: <span className="text-blue-400 font-medium">{health.queue_size}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Upload Section */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 mb-8 shadow-xl">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload Audio File
          </h2>
          
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <input
                id="file-input"
                type="file"
                accept="audio/*"
                onChange={handleFileSelect}
                disabled={uploading}
                className="block w-full text-sm text-gray-400
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-md file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-600 file:text-white
                  hover:file:bg-blue-700
                  file:cursor-pointer
                  disabled:opacity-50 disabled:cursor-not-allowed"
              />
              {selectedFile && (
                <p className="mt-2 text-sm text-gray-400">
                  Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                </p>
              )}
            </div>
            
            <button
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 
                disabled:opacity-50 disabled:cursor-not-allowed transition-colors
                flex items-center justify-center gap-2 font-medium"
            >
              {uploading ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  Uploading... {uploadProgress}%
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload
                </>
              )}
            </button>
          </div>

          {uploading && (
            <div className="mt-4">
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Jobs Section */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 shadow-xl">
          <div className="p-6 border-b border-gray-700">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <FileAudio className="w-5 h-5" />
                Jobs ({jobs.length})
              </h2>
              
              <div className="flex flex-wrap items-center gap-3">
                {/* Filter */}
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-md text-sm
                    focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Status</option>
                  <option value="queued">Queued</option>
                  <option value="processing">Processing</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                </select>

                {/* Refresh */}
                <button
                  onClick={fetchJobs}
                  disabled={loading}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-md transition-colors
                    flex items-center gap-2 text-sm font-medium"
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                  Refresh
                </button>

                {/* Clear Finished */}
                <button
                  onClick={handleClearFinished}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-md transition-colors
                    flex items-center gap-2 text-sm font-medium"
                >
                  <Trash2 className="w-4 h-4" />
                  Clear Finished
                </button>
              </div>
            </div>
          </div>

          {/* Jobs List */}
          <div className="divide-y divide-gray-700">
            {loading && jobs.length === 0 ? (
              <div className="p-12 text-center text-gray-400">
                <Loader className="w-8 h-8 animate-spin mx-auto mb-3" />
                <p>Loading jobs...</p>
              </div>
            ) : jobs.length === 0 ? (
              <div className="p-12 text-center text-gray-400">
                <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-lg">No jobs found</p>
                <p className="text-sm mt-1">Upload an audio file to get started</p>
              </div>
            ) : (
              jobs.map((job, index) => (
                <div key={job.job_id || `job-${index}`} className="p-6 hover:bg-gray-750 transition-colors">
                  <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-medium text-white truncate">
                          {job.original_filename}
                        </h3>
                        {getStatusBadge(job.status)}
                      </div>
                      
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-gray-400">
                        {job.job_id && (
                          <div>
                            <span className="font-medium">Job ID:</span>{' '}
                            <code className="text-xs bg-gray-700 px-2 py-0.5 rounded">
                              {job.job_id.substring(0, 8)}...
                            </code>
                          </div>
                        )}
                        {job.created_at && (
                          <div>
                            <span className="font-medium">Created:</span> {formatDate(job.created_at)}
                          </div>
                        )}
                        {job.updated_at && (
                          <div>
                            <span className="font-medium">Updated:</span> {formatDate(job.updated_at)}
                          </div>
                        )}
                        {job.error_message && (
                          <div className="sm:col-span-2 text-red-400">
                            <span className="font-medium">Error:</span> {job.error_message}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {job.status === 'completed' && job.job_id && (
                        <button
                          onClick={() => handleDownload(job.job_id, job.original_filename)}
                          className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-md
                            transition-colors flex items-center gap-2 text-sm font-medium"
                        >
                          <Download className="w-4 h-4" />
                          Download
                        </button>
                      )}
                      
                      {job.job_id && (
                        <button
                          onClick={() => handleDelete(job.job_id)}
                          className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-md
                            transition-colors flex items-center gap-2 text-sm font-medium"
                        >
                          <Trash2 className="w-4 h-4" />
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-12 py-6 text-center text-sm text-gray-500 border-t border-gray-800">
        <p>Quran AI Transcription Service v2.0.0</p>
      </footer>
    </div>
  );
}

export default App;
