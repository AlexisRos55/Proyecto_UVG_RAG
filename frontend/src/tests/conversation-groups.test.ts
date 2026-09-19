import { describe, expect, it } from "vitest";

import { bucketFor, groupByDate } from "@/features/chat/lib/conversation-groups";

const NOW = new Date(2026, 8, 18, 10, 0, 0); // 18 sep 2026, 10:00 local

function at(year: number, month: number, day: number, hour = 12): string {
  return new Date(year, month, day, hour).toISOString();
}

describe("bucketFor", () => {
  it("usa días naturales, no horas transcurridas", () => {
    // 23:00 de ayer está a 11 horas, pero es «Ayer», no «Hoy».
    expect(bucketFor(at(2026, 8, 17, 23), NOW)).toBe("yesterday");
    expect(bucketFor(at(2026, 8, 18, 0), NOW)).toBe("today");
  });

  it("clasifica cada tramo", () => {
    expect(bucketFor(at(2026, 8, 18), NOW)).toBe("today");
    expect(bucketFor(at(2026, 8, 17), NOW)).toBe("yesterday");
    expect(bucketFor(at(2026, 8, 14), NOW)).toBe("week");
    expect(bucketFor(at(2026, 8, 1), NOW)).toBe("month");
    expect(bucketFor(at(2026, 5, 1), NOW)).toBe("older");
  });

  it("no revienta con una fecha ilegible", () => {
    expect(bucketFor("no soy una fecha", NOW)).toBe("older");
  });

  it("trata una fecha futura como hoy en lugar de inventar un tramo", () => {
    expect(bucketFor(at(2026, 8, 20), NOW)).toBe("today");
  });
});

describe("groupByDate", () => {
  it("omite los tramos vacíos", () => {
    const groups = groupByDate([{ updatedAt: at(2026, 8, 18) }], NOW);
    expect(groups).toHaveLength(1);
    expect(groups[0].label).toBe("Hoy");
  });

  it("ordena los tramos del más reciente al más antiguo", () => {
    const groups = groupByDate(
      [{ updatedAt: at(2026, 5, 1) }, { updatedAt: at(2026, 8, 18) }, { updatedAt: at(2026, 8, 17) }],
      NOW,
    );
    expect(groups.map((g) => g.label)).toEqual(["Hoy", "Ayer", "Más antiguas"]);
  });

  it("ordena dentro del tramo por lo último tocado", () => {
    const groups = groupByDate(
      [{ updatedAt: at(2026, 8, 18, 8) }, { updatedAt: at(2026, 8, 18, 9) }],
      NOW,
    );
    expect(groups[0].items.map((i) => i.updatedAt)).toEqual([
      at(2026, 8, 18, 9),
      at(2026, 8, 18, 8),
    ]);
  });
});
