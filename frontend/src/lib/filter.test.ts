import { describe, expect, test } from "bun:test";
import { filterByStatus } from "./filter";

const itemA = { id: "a", status: "open" };
const itemB = { id: "b", status: "fixed" };
const itemC = { id: "c", status: "open" };
const items = [itemA, itemB, itemC];

describe("filterByStatus", () => {
  test("no active statuses returns everything, unfiltered", () => {
    expect(filterByStatus(items, [])).toEqual(items);
  });

  test("filters to the active statuses only", () => {
    expect(filterByStatus(items, ["open"])).toEqual([itemA, itemC]);
  });

  test("multiple active statuses are OR'd together", () => {
    expect(filterByStatus(items, ["open", "fixed"])).toEqual(items);
  });

  test("does not mutate the input array", () => {
    const copy = [...items];
    filterByStatus(items, ["open"]);
    expect(items).toEqual(copy);
  });
});
