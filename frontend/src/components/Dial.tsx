import "./Dial.css";
import { useRouter } from "../router";

const POSITIONS = [
  { path: "/", label: "sweep & findings" },
  { path: "/campaign", label: "campaign overview" },
];

/**
 * The view switch — a two-position dial, not a tab bar. A moving underline
 * marks the current position; there is nothing here shaped like a button.
 */
export function Dial() {
  const { path, navigate } = useRouter();

  return (
    <nav className="dial" aria-label="view">
      {POSITIONS.map((pos) => (
        <a
          key={pos.path}
          href={pos.path}
          aria-current={path === pos.path ? "page" : undefined}
          onClick={(e) => {
            e.preventDefault();
            navigate(pos.path);
          }}
        >
          {pos.label}
        </a>
      ))}
    </nav>
  );
}
