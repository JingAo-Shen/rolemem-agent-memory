from more_itertools import zip_equal

def pair_strictly(iter1, iter2):
    return list(zip_equal(iter1, iter2))
