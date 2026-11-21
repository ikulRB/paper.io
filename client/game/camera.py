class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.offset_x = 0
        self.offset_y = 0

    def follow(self, head):
        self.offset_x = -head[0] + self.width // 2
        self.offset_y = -head[1] + self.height // 2

    def to_screen(self, point):
        return point[0] + self.offset_x, point[1] + self.offset_y

    def to_screen_list(self, points, extra_y=0):
        return [(p[0] + self.offset_x, p[1] + self.offset_y + extra_y) for p in points]