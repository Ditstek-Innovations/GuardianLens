import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Camera, Plus, Trash2, RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/api/client';

interface DiscoveryScan {
  id: string;
  site_id: string;
  started_at: string;
  completed_at: string | null;
  scan_method: string;
  cameras_found: number;
  status: string;
}

interface DiscoveredCamera {
  id: string;
  site_id: string;
  scan_id: string;
  ip_address: string;
  hostname: string | null;
  port: number;
  model: string | null;
  manufacturer: string | null;
  rtsp_paths: string[];
  default_rtsp_path: string | null;
  resolution: string | null;
  codec: string | null;
  status: string;
  discovered_at: string;
  imported_at: string | null;
}



export function CameraDiscovery() {
  const { siteId } = useParams<{ siteId: string }>();
  
  const [subnet, setSubnet] = useState('192.168.1.0/24');
  const [scanning, setScanning] = useState(false);
  const [currentScanId, setCurrentScanId] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<DiscoveryScan | null>(null);
  const [candidates, setCandidates] = useState<DiscoveredCamera[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<DiscoveredCamera | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importName, setImportName] = useState('');
  const [importLocation, setImportLocation] = useState('');
  const [importRtspPath, setImportRtspPath] = useState('');
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Poll scan status
  useEffect(() => {
    if (!currentScanId || !scanning) return;

    const pollInterval = setInterval(async () => {
      try {
        const scan = await apiClient.get<DiscoveryScan>(`/api/v1/discovery/scans/${currentScanId}`);
        setScanStatus(scan);

        if (scan.status === 'completed' || scan.status === 'failed') {
          setScanning(false);
          
          if (scan.status === 'completed') {
            // Fetch candidates
            await fetchCandidates();
            setSuccess(`Found ${scan.cameras_found} camera(s)`);
          }
        }
      } catch (err) {
        console.error('Error polling scan status:', err);
        setError('Failed to check scan status');
        setScanning(false);
      }
    }, 1000);

    return () => clearInterval(pollInterval);
  }, [currentScanId, scanning]);

  const startScan = useCallback(async () => {
    if (!siteId || !subnet) {
      setError('Site and subnet are required');
      return;
    }

    setScanning(true);
    setError(null);
    setSuccess(null);

    try {
      const scan = await apiClient.post<DiscoveryScan>('/api/v1/discovery/scan', undefined, {
        query: { subnet, site_id: siteId }
      });
      setCurrentScanId(scan.id);
      setScanStatus(scan);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start scan');
      setScanning(false);
    }
  }, [siteId, subnet]);

  const fetchCandidates = useCallback(async () => {
    if (!siteId) return;

    try {
      const data = await apiClient.get<DiscoveredCamera[]>('/api/v1/discovery/candidates', {
        query: { site_id: siteId }
      });
      setCandidates(data);
    } catch (err) {
      console.error('Error fetching candidates:', err);
      setError('Failed to load candidates');
    }
  }, [siteId]);

  const handleImportClick = (candidate: DiscoveredCamera) => {
    setSelectedCandidate(candidate);
    setImportName(`${candidate.model || 'Camera'} - ${candidate.ip_address}`);
    setImportLocation('');
    setImportRtspPath(candidate.default_rtsp_path || '');
    setShowImportModal(true);
  };

  const handleImport = useCallback(async () => {
    if (!selectedCandidate || !importName || !importRtspPath) {
      setError('Name and RTSP path are required');
      return;
    }

    setImporting(true);
    setError(null);

    try {
      await apiClient.post(
        `/api/v1/discovery/candidates/${selectedCandidate.id}/adopt`,
        {
          candidate_id: selectedCandidate.id,
          name: importName,
          location_description: importLocation || null,
          stream_profile: 'secondary',
          sample_rate_fps: 2.0,
          rtsp_path: importRtspPath,
        }
      );

      setShowImportModal(false);
      setSuccess(`Camera "${importName}" imported successfully`);
      
      // Refresh candidates
      await fetchCandidates();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import camera');
    } finally {
      setImporting(false);
    }
  }, [selectedCandidate, importName, importLocation, importRtspPath, fetchCandidates]);

  const handleDiscard = useCallback(
    async (candidateId: string) => {
      if (!confirm('Are you sure you want to discard this candidate?')) return;

      try {
        await apiClient.delete(`/api/v1/discovery/candidates/${candidateId}`);

        setCandidates((prev) => prev.filter((c) => c.id !== candidateId));
        setSuccess('Candidate discarded');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to discard candidate');
      }
    },
    []
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Camera className="w-8 h-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">Camera Discovery</h1>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-700">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded-lg bg-green-50 border border-green-200 p-4 text-green-700">
          {success}
        </div>
      )}

      {/* Scan Panel */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Network Scan</h2>
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Subnet (CIDR)
            </label>
            <input
              type="text"
              value={subnet}
              onChange={(e) => setSubnet(e.target.value)}
              placeholder="192.168.1.0/24"
              disabled={scanning}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={startScan}
              disabled={scanning}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              {scanning ? 'Scanning...' : 'Start Scan'}
            </button>
          </div>
        </div>

        {/* Scan Progress */}
        {scanStatus && scanning && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">Scanning network...</span>
              <span className="text-sm font-medium text-gray-700">
                {scanStatus.cameras_found} found
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '100%' }} />
            </div>
          </div>
        )}
      </div>

      {/* Candidates List */}
      <div className="rounded-lg border border-gray-200 bg-white overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            Discovered Cameras ({candidates.length})
          </h2>
        </div>

        {candidates.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500">
            No cameras discovered. Run a network scan to find cameras.
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {candidates.map((camera) => (
              <div
                key={camera.id}
                className="px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-gray-900">
                        {camera.model || 'Unknown Camera'}
                      </h3>
                      <span className="inline-block px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded">
                        {camera.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 mb-3">
                      <div>
                        <span className="font-medium">IP:</span> {camera.ip_address}:{camera.port}
                      </div>
                      {camera.manufacturer && (
                        <div>
                          <span className="font-medium">Manufacturer:</span> {camera.manufacturer}
                        </div>
                      )}
                      {camera.resolution && (
                        <div>
                          <span className="font-medium">Resolution:</span> {camera.resolution}
                        </div>
                      )}
                      {camera.codec && (
                        <div>
                          <span className="font-medium">Codec:</span> {camera.codec}
                        </div>
                      )}
                    </div>

                    {camera.rtsp_paths.length > 0 && (
                      <div className="mb-3">
                        <span className="text-sm font-medium text-gray-700">
                          RTSP Paths:
                        </span>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {camera.rtsp_paths.map((path) => (
                            <span
                              key={path}
                              className="inline-block px-2 py-1 bg-gray-100 text-gray-700 text-xs font-mono rounded"
                            >
                              {path}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <p className="text-xs text-gray-500">
                      Discovered: {new Date(camera.discovered_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => handleImportClick(camera)}
                      disabled={camera.imported_at !== null}
                      className="flex items-center gap-1 px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-300 transition-colors text-sm"
                    >
                      <Plus className="w-4 h-4" />
                      Import
                    </button>
                    <button
                      onClick={() => handleDiscard(camera.id)}
                      className="flex items-center gap-1 px-3 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors text-sm"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Import Modal */}
      {showImportModal && selectedCandidate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">
              Import Camera
            </h3>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Camera Name *
                </label>
                <input
                  type="text"
                  value={importName}
                  onChange={(e) => setImportName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Location Description
                </label>
                <input
                  type="text"
                  value={importLocation}
                  onChange={(e) => setImportLocation(e.target.value)}
                  placeholder="e.g., Main Entrance"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  RTSP Path *
                </label>
                <select
                  value={importRtspPath}
                  onChange={(e) => setImportRtspPath(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">-- Select a path --</option>
                  {selectedCandidate.rtsp_paths.map((path) => (
                    <option key={path} value={path}>
                      {path}
                    </option>
                  ))}
                </select>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
                <strong>Stream URL:</strong><br />
                rtsp://{selectedCandidate.ip_address}:{selectedCandidate.port}
                {importRtspPath ? `/${importRtspPath}` : '/<path>'}
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowImportModal(false)}
                disabled={importing}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleImport}
                disabled={importing || !importName || !importRtspPath}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 transition-colors"
              >
                {importing ? 'Importing...' : 'Import Camera'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
