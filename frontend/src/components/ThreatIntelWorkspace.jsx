import React from "react";
import { Database, ShieldAlert, WifiOff } from "lucide-react";

const IntelCard = ({ title, value, icon: Icon, description }) => (
  <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
    <div className="flex items-center gap-4">
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-cyan-900/50">
        <Icon className="h-6 w-6 text-cyan-300" />
      </div>
      <div>
        <p className="text-sm text-white/60">{title}</p>
        <p className="text-2xl font-bold text-white">{value}</p>
      </div>
    </div>
    {description && <p className="mt-4 text-sm text-white/50">{description}</p>}
  </div>
);

const ThreatIntelWorkspace = ({ knownBadCount, geoIpOverrideCount }) => {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-white">Threat Intelligence Database</h2>
        <p className="mt-2 text-white/60">
          This console provides insights into the internal threat intelligence data used by Log-Sentinel's detection engine.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <IntelCard
          title="Known Malicious IPs"
          value={knownBadCount.toLocaleString()}
          icon={ShieldAlert}
          description="Number of IP addresses on the internal blacklist, used for the 'Known Bad' detection rule."
        />
        <IntelCard
          title="GeoIP Overrides"
          value={geoIpOverrideCount.toLocaleString()}
          icon={WifiOff}
          description="Number of custom IP-to-location mappings to correct or supplement the GeoIP database."
        />
        <IntelCard
          title="GeoIP Country DB"
          value="Loaded"
          icon={Database}
          description="The main GeoIP database providing country-level location data for IP addresses."
        />
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
        <h3 className="text-xl font-bold text-white">Intelligence Sources</h3>
        <p className="mt-2 text-white/60">
          The effectiveness of the detection engine relies on accurate and up-to-date intelligence. Our current sources include:
        </p>
        <ul className="mt-4 list-disc list-inside space-y-2 text-white/80">
          <li>
            <strong className="font-semibold text-cyan-300">known_bad_ips.csv:</strong> A manually curated list of IP addresses associated with malicious activity. This is the primary source for the `known_bad_ip` rule.
          </li>
          <li>
            <strong className="font-semibold text-cyan-300">geoip_overrides.json:</strong> A file to provide correct geographical locations for IPs that are commonly misplaced by standard GeoIP databases (e.g., private IPs, VPN endpoints).
          </li>
          <li>
            <strong className="font-semibold text-cyan-300">country_centroids.csv:</strong> A dataset mapping countries to their geographical centroids, used for calculating travel distance in the 'Impossible Travel' detection rule.
          </li>
        </ul>
      </div>
    </div>
  );
};

export default ThreatIntelWorkspace;
