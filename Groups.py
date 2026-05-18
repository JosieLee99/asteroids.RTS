import math
import pygame

pygame.init()
screen = pygame.display.set_mode((1920, 1080))

actual_width, actual_height = screen.get_size()

soldiers = pygame.sprite.Group()
selectedSoldiers = pygame.sprite.Group()
players = pygame.sprite.Group()
asteroids = pygame.sprite.Group()
solarSystems = pygame.sprite.Group()
currentSolarSystemID = 1
teamColors = {
    1: (255, 105, 130),
    2: (100, 170, 200)
}


def team_color(team):
    return teamColors.get(team, (255, 255, 255))


class Camera:
    def __init__(self, pos, width, height):
        self.width = width
        self.height = height
        self.pos = (0, 0)
        self.zoom = 0.7
        self.metals = 0

    def move_to_focus(self, solar_system):
        self.pos = solar_system.pos

    def zoom_out(self):
        if self.zoom > 0.5:
            self.zoom -= 0.05

    def zoom_in(self):
        if self.zoom < 1.5:
            self.zoom += 0.05

    def screen_to_world(self, screen_point):
        cx, cy = camera.pos
        zoom = camera.zoom
        return (
            (screen_point[0] - camera.width / 2) / zoom + cx,
            (screen_point[1] - camera.height / 2) / zoom + cy
        )

    def point_in_polygon(self, point, polygon):
        x, y = point
        n = len(polygon)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside


camera = Camera((0, 0), actual_width, actual_height)
