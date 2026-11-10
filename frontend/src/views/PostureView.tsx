import { Ledger, LedgerRow } from "../components/Ledger";
import { Loupe } from "../components/Loupe";
import { PostureConfidenceTick } from "../components/PostureConfidenceTick";
import { SecurityModeTick } from "../components/SecurityModeTick";
import { sampleBootState } from "../data/sampleBootState";

/**
 * BootState, per spec/contract-spec.md via ../../design/FEATURE-PLAN.md.
 * Read-only by construction — nothing here is or will ever be an Apply/
 * Revert control; see frontend/CLAUDE.md on why that's not negotiable.
 */
export function PostureView() {
  const state = sampleBootState;
  const tc = state.targetContainer;

  return (
    <>
      <div className="manifest">
        <div>
          <div className="sweep-id">
            {state.host.chip} &middot; {state.host.macosBuild}
          </div>
          <div className="sweep-label">target container posture</div>
        </div>
        <PostureConfidenceTick confidence={state.postureConfidence} />
        <div className="agents-run">
          captured {state.capturedAt} &middot; environment {state.environment} &middot; serial{" "}
          {state.host.serialMasked}
        </div>
      </div>

      <Ledger variant="boot-objects">
        <LedgerRow
          columns={[
            <span className="col-target">target container</span>,
            <span className="col-src">
              <SecurityModeTick mode={tc.securityMode} />
            </span>,
            <span className="col-score" />,
          ]}
          detail={[
            { label: "ssv enabled", value: String(tc.ssvEnabled) },
            { label: "allows custom kernel", value: String(tc.allowsCustomKernel) },
            { label: "allows third-party kexts", value: String(tc.allowsThirdPartyKexts) },
          ]}
        />
        {state.enrolledObjects.map((obj) => (
          <LedgerRow
            key={obj.role}
            columns={[
              <span className="col-target">{obj.role}</span>,
              <span className="col-src">{obj.signer}</span>,
              <span className="col-score">
                <Loupe
                  display={`${obj.sha384.slice(0, 8)}…`}
                  full={obj.sha384}
                  label={`full sha384 for ${obj.role}`}
                />
              </span>,
            ]}
            detail={[{ label: "sha384", value: obj.sha384 }]}
          />
        ))}
        {state.otherContainers.map((container, i) => (
          <LedgerRow
            key={container.volumeGroupUuid}
            columns={[
              <span className="col-target">other container {i + 1}</span>,
              <span className="col-src">{container.securityMode}</span>,
              <span className="col-score" />,
            ]}
            detail={[{ label: "volume group uuid", value: container.volumeGroupUuid }]}
          />
        ))}
      </Ledger>
    </>
  );
}
