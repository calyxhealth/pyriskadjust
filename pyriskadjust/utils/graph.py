def transitive_reduction(ancestor_dict):
    output = {k: v.copy() for (k, v) in ancestor_dict.items()}
    for i, ancestors in output.items():
        for middle in set(ancestors):
            for anc in set(ancestors) - set({middle}):
                if anc in output.get(middle, []):
                    output[i].remove(anc)
    return output
