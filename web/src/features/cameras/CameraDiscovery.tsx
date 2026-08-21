import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  AlertTriangle,
  Camera,
  LockKeyhole,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";

import { Button, Chip, Input, Modal, Select } from "@/components/ui";
import { apiClient } from "@/lib/api/client";

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

  const [subnet, setSubnet] = useState("192.168.0.0/24");
  const [scanning, setScanning] = useState(false);
  const [currentScanId, setCurrentScanId] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<DiscoveryScan | null>(null);
  const [candidates, setCandidates] = useState<DiscoveredCamera[]>([]);
  const [selectedCandidate, setSelectedCandidate] =
    useState<DiscoveredCamera | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importName, setImportName] = useState("");
  const [importLocation, setImportLocation] = useState("");
  const [importRtspPath, setImportRtspPath] = useState("");
  const [importRtspUser, setImportRtspUser] = useState("");
  const [importRtspPassword, setImportRtspPassword] = useState("");
  const [importing, setImporting] = useState(false);
  const [importingAll, setImportingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Poll scan status
  useEffect(() => {
    if (!currentScanId || !scanning) return;

    const pollInterval = setInterval(async () => {
      try {
        const scan = await apiClient.get<DiscoveryScan>(
          `/api/v1/discovery/scans/${currentScanId}`,
        );
        setScanStatus(scan);

        if (scan.status === "completed" || scan.status === "failed") {
          setScanning(false);

          if (scan.status === "completed") {
            // Fetch candidates
            await fetchCandidates();
            setSuccess(`Found ${scan.cameras_found} camera(s)`);
          }
        }
      } catch (err) {
        console.error("Error polling scan status:", err);
        setError("Failed to check scan status");
        setScanning(false);
      }
    }, 1000);

    return () => clearInterval(pollInterval);
  }, [currentScanId, scanning]);

  const startScan = useCallback(async () => {
    if (!siteId || !subnet) {
      setError("Site and subnet are required");
      return;
    }

    setScanning(true);
    setError(null);
    setSuccess(null);

    try {
      const scan = await apiClient.post<DiscoveryScan>(
        "/api/v1/discovery/scan",
        undefined,
        {
          query: { subnet, site_id: siteId },
        },
      );
      setCurrentScanId(scan.id);
      setScanStatus(scan);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start scan");
      setScanning(false);
    }
  }, [siteId, subnet]);

  const fetchCandidates = useCallback(async () => {
    if (!siteId) return;

    try {
      const data = await apiClient.get<DiscoveredCamera[]>(
        "/api/v1/discovery/candidates",
        {
          query: { site_id: siteId },
        },
      );
      setCandidates(data);
    } catch (err) {
      console.error("Error fetching candidates:", err);
      setError("Failed to load candidates");
    }
  }, [siteId]);

  const pendingCount = candidates.filter(
    (camera) => camera.imported_at === null,
  ).length;

  const handleImportAll = useCallback(async () => {
    if (!siteId) return;
    setImportingAll(true);
    setError(null);
    try {
      const result = await apiClient.post<{
        imported_count: number;
        skipped_auth_required: number;
      }>("/api/v1/discovery/candidates/adopt-pending", undefined, {
        query: { site_id: siteId },
      });
      setSuccess(
        `Imported ${result.imported_count} camera(s). Cameras requiring authentication can be configured later under Configuration → Cameras.`,
      );
      await fetchCandidates();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import cameras");
    } finally {
      setImportingAll(false);
    }
  }, [siteId, fetchCandidates]);

  const handleImportClick = (candidate: DiscoveredCamera) => {
    setSelectedCandidate(candidate);
    setImportName(`${candidate.model || "Camera"} - ${candidate.ip_address}`);
    setImportLocation("");
    setImportRtspPath(candidate.default_rtsp_path || "");
    setImportRtspUser("");
    setImportRtspPassword("");
    setShowImportModal(true);
  };

  const handleImport = useCallback(async () => {
    if (!selectedCandidate || !importName || !importRtspPath) {
      setError("Name and RTSP path are required");
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
          stream_profile: "secondary",
          sample_rate_fps: 2.0,
          rtsp_path: importRtspPath,
          ...(importRtspUser.trim() !== "" && importRtspPassword !== ""
            ? {
                rtsp_username: importRtspUser.trim(),
                rtsp_password: importRtspPassword,
              }
            : {}),
        },
      );

      setShowImportModal(false);
      setSuccess(`Camera "${importName}" imported successfully`);

      // Refresh candidates
      await fetchCandidates();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import camera");
    } finally {
      setImporting(false);
    }
  }, [
    selectedCandidate,
    importName,
    importLocation,
    importRtspPath,
    importRtspUser,
    importRtspPassword,
    fetchCandidates,
  ]);

  const handleDiscard = useCallback(async (candidateId: string) => {
    if (!confirm("Are you sure you want to discard this candidate?")) return;

    try {
      await apiClient.delete(`/api/v1/discovery/candidates/${candidateId}`);

      setCandidates((prev) => prev.filter((c) => c.id !== candidateId));
      setSuccess("Candidate discarded");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to discard candidate",
      );
    }
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Camera className="h-8 w-8 text-brand-mark" />
          <div>
            <h1 className="text-3xl font-bold text-fg">Camera Discovery</h1>
            <p className="mt-1 text-sm text-fg-muted">
              Find RTSP cameras now and add their login immediately or later.
            </p>
          </div>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div
          role="alert"
          className="rounded-card border border-danger bg-danger-subtle p-4 text-danger"
        >
          {error}
        </div>
      )}
      {success && (
        <div
          role="status"
          className="rounded-card border border-ok bg-ok-subtle p-4 text-ok"
        >
          {success}
        </div>
      )}

      {/* Scan Panel */}
      <section className="rounded-card border border-border bg-surface-1 p-6 shadow-ambient">
        <h2 className="mb-4 text-lg font-semibold text-fg">Network Scan</h2>
        <div className="flex flex-col gap-4 sm:flex-row">
          <div className="flex-1">
            <label
              htmlFor="camera-discovery-subnet"
              className="mb-2 block text-sm font-medium text-fg"
            >
              Subnet (CIDR)
            </label>
            <Input
              id="camera-discovery-subnet"
              type="text"
              value={subnet}
              onChange={(e) => setSubnet(e.target.value)}
              placeholder="192.168.0.0/24"
              disabled={scanning}
            />
          </div>
          <div className="flex items-end sm:shrink-0">
            <Button
              onClick={startScan}
              disabled={scanning}
              isLoading={scanning}
              className="w-full sm:w-auto"
            >
              {!scanning ? <RefreshCw className="h-4 w-4" /> : null}
              {scanning ? "Scanning..." : "Start Scan"}
            </Button>
          </div>
        </div>

        {/* Scan Progress */}
        {scanStatus && scanning && (
          <div className="mt-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm text-fg-muted">Scanning network...</span>
              <span className="text-sm font-medium text-fg">
                {scanStatus.cameras_found} found
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-surface-3">
              <div className="h-2 w-full animate-pulse rounded-full bg-brand-500" />
            </div>
          </div>
        )}
      </section>

      {/* Candidates List */}
      <section className="overflow-hidden rounded-card border border-border bg-surface-1 shadow-ambient">
        <div className="flex flex-col items-start justify-between gap-3 border-b border-border px-6 py-4 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-lg font-semibold text-fg">
              Discovered Cameras ({candidates.length})
            </h2>
            <p className="mt-1 text-sm text-fg-muted">
              Authentication-required cameras can be imported now. Add their
              RTSP login later from Configuration → Cameras → Replace
              credential.
            </p>
          </div>
          <Button
            variant="ok"
            size="sm"
            onClick={() => void handleImportAll()}
            disabled={importingAll || pendingCount === 0}
            isLoading={importingAll}
            className="shrink-0"
          >
            {!importingAll ? <Plus className="h-4 w-4" /> : null}
            {importingAll ? "Importing…" : `Import all (${pendingCount})`}
          </Button>
        </div>

        {candidates.length === 0 ? (
          <div className="px-6 py-10 text-center text-fg-muted">
            No cameras discovered. Run a network scan to find cameras.
          </div>
        ) : (
          <div className="divide-y divide-border">
            {candidates.map((camera) => (
              <div
                key={camera.id}
                className="px-6 py-4 transition-colors duration-120 hover:bg-surface-2"
              >
                <div className="flex flex-col items-start justify-between gap-4 sm:flex-row">
                  <div className="min-w-0 flex-1">
                    <div className="mb-2 flex items-center gap-3">
                      <h3 className="font-semibold text-fg">
                        {camera.model || "Unknown Camera"}
                      </h3>
                      {camera.imported_at !== null ? (
                        <Chip variant="neutral">Imported</Chip>
                      ) : camera.resolution === "Unknown (Auth Required)" ? (
                        <Chip
                          variant="warn"
                          icon={<LockKeyhole className="h-3.5 w-3.5" />}
                        >
                          Login required
                        </Chip>
                      ) : (
                        <Chip variant="ok">{camera.status}</Chip>
                      )}
                    </div>

                    <div className="mb-3 grid grid-cols-1 gap-2 text-sm text-fg-muted sm:grid-cols-2 sm:gap-4">
                      <div>
                        <span className="font-medium">IP:</span>{" "}
                        {camera.ip_address}:{camera.port}
                      </div>
                      {camera.manufacturer && (
                        <div>
                          <span className="font-medium">Manufacturer:</span>{" "}
                          {camera.manufacturer}
                        </div>
                      )}
                      {camera.resolution && (
                        <div>
                          <span className="font-medium">Resolution:</span>{" "}
                          {camera.resolution}
                        </div>
                      )}
                      {camera.codec && (
                        <div>
                          <span className="font-medium">Codec:</span>{" "}
                          {camera.codec}
                        </div>
                      )}
                    </div>

                    {camera.rtsp_paths.length > 0 && (
                      <div className="mb-3">
                        <span className="text-sm font-medium text-fg">
                          RTSP Paths:
                        </span>
                        <div className="mt-1 flex flex-wrap gap-2">
                          {camera.rtsp_paths.map((path) => (
                            <span
                              key={path}
                              className="inline-block rounded-sm bg-surface-3 px-2 py-1 font-mono text-xs text-fg-muted"
                            >
                              {path}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <p className="text-xs text-fg-faint">
                      Discovered:{" "}
                      {new Date(camera.discovered_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex shrink-0 gap-2 sm:ml-4">
                    <Button
                      variant="ok"
                      size="sm"
                      onClick={() => handleImportClick(camera)}
                      disabled={camera.imported_at !== null}
                    >
                      <Plus className="h-4 w-4" />
                      {camera.imported_at !== null ? "Imported" : "Import"}
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleDiscard(camera.id)}
                      aria-label={`Discard camera ${camera.ip_address}`}
                    >
                      <Trash2 className="h-4 w-4" />
                      <span className="hidden sm:inline">Discard</span>
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Import Modal */}
      {showImportModal && selectedCandidate && (
        <Modal title="Import Camera" onClose={() => setShowImportModal(false)}>
          <div className="mb-6 space-y-4">
            {selectedCandidate.resolution === "Unknown (Auth Required)" ? (
              <div className="flex items-start gap-2 rounded-control border border-warn bg-warn-subtle p-3 text-sm text-warn">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <p>
                  This camera requires authentication. You can import it without
                  a login now; it will show as stream down until you add the
                  RTSP URL from Configuration → Cameras → Replace credential.
                </p>
              </div>
            ) : null}
            <div>
              <label
                htmlFor="discovery-camera-name"
                className="mb-2 block text-sm font-medium text-fg"
              >
                Camera Name *
              </label>
              <Input
                id="discovery-camera-name"
                type="text"
                value={importName}
                onChange={(e) => setImportName(e.target.value)}
              />
            </div>

            <div>
              <label
                htmlFor="discovery-camera-location"
                className="mb-2 block text-sm font-medium text-fg"
              >
                Location Description
              </label>
              <Input
                id="discovery-camera-location"
                type="text"
                value={importLocation}
                onChange={(e) => setImportLocation(e.target.value)}
                placeholder="e.g., Main Entrance"
              />
            </div>

            <div>
              <label
                htmlFor="discovery-rtsp-path"
                className="mb-2 block text-sm font-medium text-fg"
              >
                RTSP Path *
              </label>
              <Select
                id="discovery-rtsp-path"
                value={importRtspPath}
                onChange={(e) => setImportRtspPath(e.target.value)}
              >
                <option value="">-- Select a path --</option>
                {selectedCandidate.rtsp_paths.map((path) => (
                  <option key={path} value={path}>
                    {path}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <p className="mb-2 text-sm font-medium text-fg">
                Camera login (optional)
              </p>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="text"
                  value={importRtspUser}
                  onChange={(e) => setImportRtspUser(e.target.value)}
                  placeholder="Username"
                  autoComplete="off"
                  aria-label="RTSP username"
                />
                <Input
                  type="password"
                  value={importRtspPassword}
                  onChange={(e) => setImportRtspPassword(e.target.value)}
                  placeholder="Password"
                  autoComplete="new-password"
                  aria-label="RTSP password"
                />
              </div>
              <p className="mt-1 text-xs text-fg-muted">
                Leave both blank to add the complete RTSP credential later.
              </p>
            </div>

            <div className="rounded-control border border-border bg-brand-subtle p-3 text-sm text-brand-ink">
              <strong>This camera’s stream URL</strong> (sealed on import; the
              edge uses this, not a shared static URL):
              <br />
              rtsp://
              {importRtspUser.trim() !== ""
                ? `${importRtspUser.trim()}:••••@`
                : ""}
              {selectedCandidate.ip_address}:{selectedCandidate.port}
              {importRtspPath ? `/${importRtspPath}` : "/<path>"}
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => setShowImportModal(false)}
              disabled={importing}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              variant="ok"
              onClick={handleImport}
              disabled={importing || !importName || !importRtspPath}
              isLoading={importing}
              className="flex-1"
            >
              {importing
                ? "Importing..."
                : selectedCandidate.resolution === "Unknown (Auth Required)" &&
                    importRtspUser.trim() === ""
                  ? "Import now"
                  : "Import Camera"}
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
