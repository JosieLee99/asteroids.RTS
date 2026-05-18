import math
import random

import pygame

import Groups
from Asteroid import Asteroid

mapHexagons = []
ASTEROIDS_PER_FIELD_SYSTEM = 30


class ManageSolarSystem:
    def __init__(self):
        super().__init__()

    def spawnMap(self):
        radius = 1500
        padding = 20
        spacing = radius * math.sqrt(3) + padding
        positions = [(0, 0)]

        for i in range(6):
            angle = math.radians(i * 60 + 30)
            positions.append((spacing * math.cos(angle), spacing * math.sin(angle)))

        for pos in positions:
            mapHexagons.append(SolarSystem.get_hexagon_points(radius, pos))

    def spawnBigMap(self, radius, padding):
        spacing = radius * math.sqrt(3) + padding
        positions = [(0, 0)]

        for i in range(6):
            angle = math.radians(i * 60 + 30)
            positions.append((spacing * math.cos(angle), spacing * math.sin(angle)))

        for i in range(6):
            angle_a = math.radians(i * 60 + 30)
            positions.append(((spacing * 2) * math.cos(angle_a), ((spacing * 2) * math.sin(angle_a))))

            angle_b = math.radians(i * 60)
            positions.append(
                ((spacing * math.sqrt(3)) * math.cos(angle_b), ((spacing * math.sqrt(3)) * math.sin(angle_b)))
            )

        mapHexagons.clear()
        for pos in positions:
            solar_system = SolarSystem(0, pos, [])
            solar_system.hexagonPoints = solar_system.get_hexagon_points(radius, pos)
            mapHexagons.append(solar_system.hexagonPoints)

        self.assign_visual_solar_system_values()
        self.spawn_top_and_bottom_asteroid_fields(ASTEROIDS_PER_FIELD_SYSTEM)

    def assign_visual_solar_system_values(self):
        solar_systems = sorted(Groups.solarSystems, key=lambda solar_system: (solar_system.pos[1], solar_system.pos[0]))
        for system_value, solar_system in enumerate(solar_systems, start=1):
            solar_system.solarSystemID = system_value
            solar_system.id = system_value

    def spawn_top_and_bottom_asteroid_fields(self, asteroids_per_system=ASTEROIDS_PER_FIELD_SYSTEM):
        solar_systems = Groups.solarSystems.sprites()
        if len(solar_systems) == 0:
            return

        top_solar_system = min(solar_systems, key=lambda solar_system: solar_system.pos[1])
        bottom_solar_system = max(solar_systems, key=lambda solar_system: solar_system.pos[1])
        target_solar_systems = (
            self.closest_solar_systems(top_solar_system, 3)
            + self.closest_solar_systems(bottom_solar_system, 3)
        )

        for solar_system in set(target_solar_systems):
            self.assign_asteroids_to_solar_system(solar_system.id, asteroids_per_system)

    def assign_asteroids_to_solar_system(self, system_value, asteroid_count=None):
        asteroid_count = ASTEROIDS_PER_FIELD_SYSTEM if asteroid_count is None else asteroid_count
        solar_system = self.get_solar_system_by_value(system_value)
        if solar_system is None:
            return

        for _ in range(asteroid_count):
            asteroid = Asteroid(
                Groups.screen,
                random.randint(4, 8),
                None,
                self.random_point_in_solar_system(solar_system),
                (0, 0),
                0,
            )
            asteroid.solarSystem = solar_system

    def get_solar_system_by_value(self, system_value):
        for solar_system in Groups.solarSystems:
            if solar_system.id == system_value:
                return solar_system
        return None

    def closest_solar_systems(self, solar_system, count):
        return sorted(
            [other for other in Groups.solarSystems if other is not solar_system],
            key=lambda other: (other.pos[0] - solar_system.pos[0]) ** 2 + (other.pos[1] - solar_system.pos[1]) ** 2,
        )[:count]

    def random_point_in_solar_system(self, solar_system):
        xs = [point[0] for point in solar_system.hexagonPoints]
        ys = [point[1] for point in solar_system.hexagonPoints]

        while True:
            point = (
                random.uniform(min(xs), max(xs)),
                random.uniform(min(ys), max(ys)),
            )
            if Groups.camera.point_in_polygon(point, solar_system.hexagonPoints):
                return point


class SolarSystem(pygame.sprite.Sprite):
    def __init__(self, solarSystemID, pos, lines):
        super().__init__()
        self.lines = None
        self.pos = pos
        self.hexagonPoints = self.get_hexagon_points(1500, (0, 0))
        self._cached_zoom = None
        self._cached_pos = None
        self._cached_screen_hexagons = []
        Groups.solarSystems.add(self)
        self.solarSystemID = solarSystemID
        self.id = solarSystemID

    def get_hexagon_points(self, radius, center):
        points = []
        h, k = center
        for i in range(6):
            theta = (2 * math.pi * i) / 6
            x = h + radius * math.cos(theta)
            y = k + radius * math.sin(theta)
            points.append((x, y))
        return points

    def draw(self, screen):
        if self._cached_zoom != Groups.camera.zoom or self._cached_pos != Groups.camera.pos:
            self._cached_zoom = Groups.camera.zoom
            self._cached_pos = Groups.camera.pos
            self._cached_screen_hexagons = []
            for hexagon in mapHexagons:
                self._cached_screen_hexagons.append(
                    [
                        (
                            int((p[0] - Groups.camera.pos[0]) * Groups.camera.zoom + Groups.camera.width / 2),
                            int((p[1] - Groups.camera.pos[1]) * Groups.camera.zoom + Groups.camera.height / 2),
                        )
                        for p in hexagon
                    ]
                )

        for screen_hex in self._cached_screen_hexagons:
            pygame.draw.lines(screen, (255, 255, 255), True, screen_hex, 2)

    def get_hexagon_axes(self, points):
        axes = []
        for i in range(len(points)):
            a = points[i]
            b = points[(i + 1) % len(points)]
            edge = (b[0] - a[0], b[1] - a[1])
            length = math.sqrt(edge[0] ** 2 + edge[1] ** 2)
            if length == 0:
                continue
            normal = (-edge[1] / length, edge[0] / length)
            axes.append(normal)
        return axes

    def confine_to_hexagon(self, pos, world_points, velocity):
        hex_points = self.hexagonPoints
        center = (
            sum(p[0] for p in hex_points) / len(hex_points),
            sum(p[1] for p in hex_points) / len(hex_points),
        )

        for i in range(len(hex_points)):
            a = hex_points[i]
            b = hex_points[(i + 1) % len(hex_points)]

            edge = (b[0] - a[0], b[1] - a[1])
            length = math.sqrt(edge[0] ** 2 + edge[1] ** 2)
            if length == 0:
                continue

            inward = (-edge[1] / length, edge[0] / length)
            to_center = (center[0] - a[0], center[1] - a[1])
            if to_center[0] * inward[0] + to_center[1] * inward[1] < 0:
                inward = (-inward[0], -inward[1])

            max_penetration = 0
            for p in world_points:
                to_p = (p[0] - a[0], p[1] - a[1])
                dist = to_p[0] * inward[0] + to_p[1] * inward[1]
                if dist < max_penetration:
                    max_penetration = dist

            if max_penetration < 0:
                correction = -max_penetration + 0.01
                pos = (
                    pos[0] + inward[0] * correction,
                    pos[1] + inward[1] * correction,
                )
                world_points = [
                    (p[0] + inward[0] * correction, p[1] + inward[1] * correction)
                    for p in world_points
                ]

                movement = (velocity[0], -velocity[1])
                movement_dot = movement[0] * inward[0] + movement[1] * inward[1]
                if movement_dot < 0:
                    movement = (
                        movement[0] - movement_dot * inward[0],
                        movement[1] - movement_dot * inward[1],
                    )
                    velocity = (movement[0], -movement[1])

        return pos, velocity
