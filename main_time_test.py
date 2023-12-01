def check_score(beam_states, cur_board):
    pos_arr = [
        [0, 3],
        [1, 3],
        [2, 3],
        [2, 4],
        [1, 4],
        [0, 4],
        [0, 5],
        [1, 5],
        [2, 5]
    ]

    zero_indexes = [i for i, value in enumerate(beam_states) if value == 0]
    map = [8, 7, 6, 3, 4, 5, 2, 1, 0]

    for index, pos in enumerate(pos_arr):
        if pos == zero_indexes:
            cur_board[map.index(index)] = 1 #if self.current_player else 2
            return True

    return False


cur_board = [0, 0, 0,
             0, 0, 0,
             0, 0, 0]
binary_array = [1, 1, 0, 1, 0, 1]
result = check_score(binary_array, cur_board)
print(result, cur_board)
