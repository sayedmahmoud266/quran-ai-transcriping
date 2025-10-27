import axios from 'axios';

const API_BASE_URL = import.meta.env.DEV ? '/api' : '';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const jobsApi = {
  // Get all jobs
  getAllJobs: async (status = null) => {
    const params = status ? { status } : {};
    const response = await api.get('/jobs', { params });
    return response.data;
  },

  // Get job status
  getJobStatus: async (jobId) => {
    const response = await api.get(`/jobs/${jobId}/status`);
    return response.data;
  },

  // Get job metadata
  getJobMetadata: async (jobId) => {
    const response = await api.get(`/jobs/${jobId}/metadata`);
    return response.data;
  },

  // Upload audio file for transcription
  uploadAudio: async (file, onProgress) => {
    const formData = new FormData();
    formData.append('audio_file', file);

    const response = await api.post('/transcribe/async', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });

    return response.data;
  },

  // Download job result
  downloadResult: async (jobId, filename) => {
    const response = await api.get(`/jobs/${jobId}/download`, {
      responseType: 'blob',
    });

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename || `result_${jobId}.zip`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  // Delete job
  deleteJob: async (jobId) => {
    const response = await api.delete(`/jobs/${jobId}`);
    return response.data;
  },

  // Clear finished jobs
  clearFinishedJobs: async () => {
    const response = await api.delete('/jobs/finished');
    return response.data;
  },

  // Resume queue
  resumeQueue: async () => {
    const response = await api.post('/jobs/resume');
    return response.data;
  },

  // Health check
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
