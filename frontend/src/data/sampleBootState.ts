import type { BootState } from "./types";

/**
 * Illustrative sample data only — see ../../../design/README.md. Shaped
 * like a real `cargo run -- evaluate --json` result on an owned Mac in
 * Full security mode with sudo cached, per spec/contract-spec.md's
 * BootState contract. Not a capture from a real device.
 */
export const sampleBootState: BootState = {
  schemaVersion: 2,
  capturedAt: "2026-11-11T02:12:04Z",
  environment: "MacOS",
  postureConfidence: "measured",
  host: {
    chip: "Apple M2",
    macosBuild: "25D125",
    serialMasked: "••••P0K2",
  },
  targetContainer: {
    securityMode: "Full",
    ssvEnabled: true,
    allowsCustomKernel: false,
    allowsThirdPartyKexts: false,
  },
  enrolledObjects: [
    { role: "LLB", signer: "Apple", sha384: "a3f1".padEnd(96, "0") },
    { role: "iBoot", signer: "Apple", sha384: "9c42".padEnd(96, "0") },
    { role: "KernelCache", signer: "Apple", sha384: "71e0".padEnd(96, "0") },
  ],
  otherContainers: [{ volumeGroupUuid: "B2F1-9A3E-REDACTED", securityMode: "Unknown" }],
};

/** The same device read without a cached sudo credential — fails closed. */
export const sampleBootStateUnmeasured: BootState = {
  ...sampleBootState,
  capturedAt: "2026-11-11T02:14:51Z",
  postureConfidence: "untrusted-read",
  targetContainer: {
    ...sampleBootState.targetContainer,
    securityMode: "Unknown",
  },
};
