def draw_board(board):
    cells = [c if c != " " else str(i) for i,c in enumerate(board)]
    return f"""
 {cells[0]} | {cells[1]} | {cells[2]}
---+---+---
 {cells[3]} | {cells[4]} | {cells[5]}
---+---+---
 {cells[6]} | {cells[7]} | {cells[8]}
"""

def help_text():
    return """\
LỆNH:
  /name <ten>          đặt tên
  /rooms               liệt kê phòng
  /create <room>       tạo và vào phòng
  /join <room>         vào phòng có sẵn
  move <0..8>          đánh vào ô 0..8
  /leave               rời phòng
  /help                xem trợ giúp
"""
