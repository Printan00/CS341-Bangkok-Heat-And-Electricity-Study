"""Small statistics for the real-file tests (standard library only): Spearman, permutation test, random weights."""
import random
import statistics


def average_ranks(values):
    """1-based ranks, tied values share the average of their positions."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x, y):
    return statistics.correlation(average_ranks(x), average_ranks(y))


def permutation_p(a, b, rounds=10000, seed=1):
    """Two-sided p of the difference of means between a and b, by shuffling group labels."""
    rng = random.Random(seed)
    pooled = list(a) + list(b)
    observed = abs(statistics.fmean(a) - statistics.fmean(b))
    hits = 0
    for _ in range(rounds):
        rng.shuffle(pooled)
        hits += abs(statistics.fmean(pooled[:len(a)]) - statistics.fmean(pooled[len(a):])) >= observed
    return (hits + 1) / (rounds + 1)


def dirichlet_ones(n, rng):
    """One draw from Dirichlet(1, ..., 1): every weight vector that sums to 1 is equally likely."""
    g = [rng.expovariate(1.0) for _ in range(n)]
    total = sum(g)
    return [v / total for v in g]
