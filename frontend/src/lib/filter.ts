/**
 * Filters a list of status-bearing items down to the active statuses. An
 * empty `activeStatuses` means no filter is applied — matches the legend's
 * "all checkboxes unchecked = show everything" behavior.
 */
export function filterByStatus<T extends { status: string }>(
  items: readonly T[],
  activeStatuses: readonly string[],
): T[] {
  if (activeStatuses.length === 0) {
    return [...items];
  }
  return items.filter((item) => activeStatuses.includes(item.status));
}
