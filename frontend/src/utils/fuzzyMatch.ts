export interface FuzzyResult {
  score: number;
  indices: number[];
}

export function fuzzyMatch(query: string, target: string): FuzzyResult {
  const q = query.toLowerCase();
  const t = target.toLowerCase();
  const indices: number[] = [];
  let score = 0;
  let qi = 0;
  let consecutive = 0;

  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) {
      indices.push(ti);
      consecutive++;
      score += consecutive;
      if (ti === 0 || t[ti - 1] === ' ' || t[ti - 1] === '/' || t[ti - 1] === '-') {
        score += 2;
      }
      qi++;
    } else {
      consecutive = 0;
    }
  }

  if (qi < q.length) return { score: 0, indices: [] };

  const lengthPenalty = Math.max(0, 1 - (t.length - q.length) * 0.01);
  return { score: score * lengthPenalty, indices };
}
