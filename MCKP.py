# Source: https://gist.github.com/USM-F/1287f512de4ffb2fb852e98be1ac271d
import copy
from itertools import chain


# groups is list of integers in ascending order without gaps

def getRow(lists, row):
    res = []
    for l in lists:
        for i in range(len(l)):
            if i == row:
                res.append(l[i])
    return res


def multipleChoiceKnapsack(W, weights, values, groups):
    n = len(values)
    K = [[0 for x in range(W + 1)] for x in range(n + 1)]

    for w in range(W + 1):
        for i in range(n + 1):
            if i == 0 or w == 0:
                K[i][w] = 0
            elif weights[i - 1] <= w:
                sub_max = 0
                prev_group = groups[i - 1] - 1
                sub_K = getRow(K, w - weights[i - 1])
                for j in range(n + 1):
                    if groups[j - 1] == prev_group and sub_K[j] > sub_max:
                        sub_max = sub_K[j]
                K[i][w] = max(sub_max + values[i - 1], K[i - 1][w])
            else:
                K[i][w] = K[i - 1][w]
        if w % 10 == 0:
            print(str(w/W*100) + " %")

    # stores the result of Knapsack
    res = K[n][W]
    sol = []

    w = W
    for i in range(n, 0, -1):
        if res <= 0:
            break
        # either the result comes from the
        # top (K[i-1][w]) or from (val[i-1]
        # + K[i-1] [w-wt[i-1]]) as in Knapsack
        # table. If it comes from the latter
        # one/ it means the item is included.
        if res == K[i - 1][w]:
            continue
        else:

            # This item is included.
            sol.append(i - 1)
            print(i - 1)

            #sub_max = 0
            #prev_group = groups[i - 1] - 1
            #sub_K = getRow(K, w - weights[i - 1])
            #for j in range(n + 1):
            #    if groups[j - 1] == prev_group and sub_K[j] > sub_max:
            #        sub_max = sub_K[j]

            # Since this weight is included
            # its value is deducted
            res = res - values[i - 1]
            w = w - weights[i - 1]

    return K[n][W], sol


# Source: https://github.com/je-suis-tm/recursion-and-dynamic-programming/blob/master/knapsack%20multiple%20choice.py

def knapsack_multichoice(total_weight, values, weights, groups):
    # python starts index at 0 which is why we use len(values)+1
    # create a nested list with size of (number of items+1)*(weights+1)
    array = [[0 for _ in range(total_weight + 1)] for _ in
             range(len(values) + 1)]
    path = [[[] for _ in range(total_weight + 1)] for _ in
            range(len(values) + 1)]

    # now we begin our traversal on all elements in matrix
    # note we would be using i-1 to imply item i
    for i in range(1, len(values) + 1):
        for j in range(1, total_weight + 1):

            # this is the part to check if adding item i would exceed the current capacity j
            # if it does,we go to the previous status
            # if not,we shall find out whether adding item i would be the new optimal
            if weights[i - 1] <= j:

                # we only select one item from each group
                # we will find the item that maximizes the value in each group
                prev_group = groups[i - 1] - 1

                # initialize
                subset_max = 0
                target = 0

                # get column of the matrix
                subset = [row[j - weights[i - 1]] for row in array]

                # find the item that maximizes the value in the previous group
                for k in range(len(values) + 1):
                    if groups[k - 1] == prev_group and subset[k] > subset_max:
                        subset_max = subset[k]
                        target = k

                if not path[target][j - weights[i - 1]]:
                    comp = True
                else:
                    comp = weights[i - 1] < weights[path[target][j - weights[i - 1]][-1]]
                # dynamic programming
                if subset_max + values[i - 1] > array[i - 1][j]:
                    array[i][j] = subset_max + values[i - 1]
                    path[i][j] = path[target][j - weights[i - 1]] + [i - 1]
                elif subset_max + values[i - 1] == array[i - 1][j] and comp:
                    array[i][j] = subset_max + values[i - 1]
                    path[i][j] = path[target][j - weights[i - 1]] + [i - 1]
                else:
                    array[i][j] = array[i - 1][j]
                    path[i][j] = path[i - 1][j]
            else:
                array[i][j] = array[i - 1][j]
                path[i][j] = path[i - 1][j]

        if i % 100 == 0:
            print(str(i/len(values)*100) + " %")

    flat_array = list(chain.from_iterable(array))
    flat_path = list(chain.from_iterable(path))

    n_groups = len(set(groups))

    solution, index_path = get_contrained_solution(flat_array, flat_path, n_groups)

    return solution, index_path


def get_contrained_solution(scores, paths, count):

    score = scores[-1]
    path = paths[-1]

    scores_paths = list(zip(scores, paths))
    sorted_by_score = sorted(scores_paths, key=lambda tup: tup[0], reverse=True)

    for top_score_path in sorted_by_score:
        if len(top_score_path[1]) == count:
            score = top_score_path[0]
            path = top_score_path[1]
            break

    return score, path


# Original source: https://nickgavalas.com/solving-the-multiple-choice-knapsack-problem/
# Translated by pabloroldan98

def knapsack_multichoice_onepick(weights, values, max_weight, verbose=False):
    if len(weights) == 0:
        return 0

    last_array = [-1 for _ in range(max_weight + 1)]
    last_path = [[] for _ in range(max_weight + 1)]
    for i in range(len(weights[0])):
        if weights[0][i] < max_weight:
            if last_array[weights[0][i]] < values[0][i]:
                last_array[weights[0][i]] = values[0][i]
                last_path[weights[0][i]] = [(0, i)]
            # last_array[weight[0][i]] = max(last_array[weight[0][i]], value[0][i])

    threshold = 0
    for i in range(1, len(weights)):
        current_array = [-1 for _ in range(max_weight + 1)]
        current_path = [[] for _ in range(max_weight + 1)]
        for j in range(len(weights[i])):
            for k in range(weights[i][j], max_weight + 1):
                if last_array[k - weights[i][j]] > 0:
                    if current_array[k] < last_array[k - weights[i][j]] + values[i][j]:
                        current_array[k] = last_array[k - weights[i][j]] + values[i][j]
                        current_path[k] = copy.deepcopy(last_path[k - weights[i][j]])
                        current_path[k].append((i, j))
                    # current_array[k] = max(current_array[k], last_array[k - weight[i][j]] + value[i][j])
            if verbose:
                percent = (i*len(weights[i])+j)/(len(weights)*len(weights[i]))*100
                if percent >= threshold:
                    print(str(percent) + " %")
                    threshold = threshold + 1
        last_array = current_array
        last_path = current_path
    if verbose:
        print("100 %")
    solution, index_path = get_onepick_solution(last_array, last_path)

    return solution, index_path


def get_onepick_solution(scores, paths):
    scores_paths = list(zip(scores, paths))
    scores_paths_by_score = sorted(scores_paths, key=lambda tup: tup[0], reverse=True)

    return scores_paths_by_score[0][0], scores_paths_by_score[0][1]


# Example
values = [60, 100, 120, 20, 20, 30]
weights = [10, 20, 60, 20, 30, 20]
groups = [0, 0, 1, 1, 2, 2]
W = 80
#print(multipleChoiceKnapsack(W, weights, values, groups))  # 220

#print(knapsack_multichoice(W, values, weights, groups))  # 220


# Example
# values = [[6, 10], [12, 2], [2, 3]]
# weights = [[1, 2], [6, 2], [3, 2]]
# W = 7
#
# print(knapsack_multichoice_onepick(weights, values, W))  # (15, [(0, 1), (1, 1), (2, 1)])
