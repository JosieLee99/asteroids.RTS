import math
import random

import pygame

import Groups


class Asteroid(pygame.sprite.Sprite):
    def __init__(self, screen, points, lines, pos, velocity, rot):
        super().__init__()
        Groups.asteroids.add(self)
        self.screen = screen
        self.points = points
        self.pos = pos
        self.radius = random.randint(10, random.randint(100, 200))
        self.mass = math.pi * self.radius
        self.lines = self.get_circle_points(self.radius, points, (0, 0))
        self.velocity = velocity
        self.rot = rot
        self.health = 100
        self.solarSystem = None
        self.collisionRadius = self.radius + 10

    def setPosition(self):
        self.pos = list(self.pos)
        self.pos[0] += self.velocity[0]
        self.pos = tuple(self.pos)

        self.pos = list(self.pos)
        self.pos[1] -= self.velocity[1]
        self.pos = tuple(self.pos)

    def bounce_off_hexagon(self):
        hex_points = Groups.camera.pentagon_points

        for i in range(len(hex_points)):
            a = hex_points[i]
            b = hex_points[(i + 1) % len(hex_points)]

            edge = (b[0] - a[0], b[1] - a[1])
            length = math.sqrt(edge[0] ** 2 + edge[1] ** 2)
            inward = (edge[1] / length, -edge[0] / length)

            to_pos = (self.pos[0] - a[0], self.pos[1] - a[1])
            dist = to_pos[0] * inward[0] + to_pos[1] * inward[1]

            if dist < 0:
                vel_dot = self.velocity[0] * inward[0] + self.velocity[1] * inward[1]
                if vel_dot < 0:
                    self.velocity = (
                        self.velocity[0] - 2 * vel_dot * inward[0],
                        self.velocity[1] - 2 * vel_dot * inward[1],
                    )

    def scale_points(self, center, scale):
        cx, cy = center
        return [
            (cx + (p[0] - cx) * scale, cy + (p[1] - cy) * scale)
            for p in self.lines
        ]

    def world_to_screen(self, point, camera_pos, zoom):
        cx, cy = Groups.camera.pos
        return (
            (point[0] - cx) * zoom + Groups.camera.width / 2,
            (point[1] - cy) * zoom + Groups.camera.height / 2,
        )

    def spawnAsteroidVector(self):
        world_points = self.get_world_points()
        if self.is_visible_on_screen():
            screen_points = [self.world_to_screen(p, Groups.camera.pos, Groups.camera.zoom) for p in world_points]
            pygame.draw.lines(self.screen, (100, 100, 100), True, screen_points, 2)

        self.checkAsteroidCollision()

    def get_world_points(self):
        return [(line[0] + self.pos[0], line[1] + self.pos[1]) for line in self.lines]

    def is_visible_on_screen(self, margin=150):
        screen_pos = self.world_to_screen(self.pos, Groups.camera.pos, Groups.camera.zoom)
        screen_radius = self.collisionRadius * Groups.camera.zoom
        return not (
            screen_pos[0] + screen_radius < -margin
            or screen_pos[0] - screen_radius > Groups.camera.width + margin
            or screen_pos[1] + screen_radius < -margin
            or screen_pos[1] - screen_radius > Groups.camera.height + margin
        )

    def get_circle_points(self, radius, num_points, center):
        self.lines = []
        h, k = center
        for i in range(num_points):
            theta = (2 * math.pi * i) / num_points
            x = h + radius * math.cos(theta)
            y = k + radius * math.sin(theta)
            self.lines.append((x + random.randint(-5, 5), y + random.randint(-5, 5)))
        return self.lines

    def rotate_points(self, points, center, angle_degrees):
        self.rot += angle_degrees

        angle_rad = math.radians(angle_degrees - 180)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        cx, cy = center

        rotated = []
        for x, y in points:
            tx = x - cx
            ty = y - cy + 20

            rx = tx * cos_a - ty * sin_a
            ry = tx * sin_a + ty * cos_a
            rotated.append((rx + cx, ry + cy))

        self.rot += angle_degrees

        if self.rot > 360:
            self.rot -= 360
        elif self.rot < -360:
            self.rot += 360

        return rotated

    def remove_point_near_world_pos(self, world_pos, inward_strength=0.12):
        if len(self.lines) <= 3:
            self.kill()
            return True

        local_pos = (world_pos[0] - self.pos[0], world_pos[1] - self.pos[1])
        hit_index = min(
            range(len(self.lines)),
            key=lambda i: (self.lines[i][0] - local_pos[0]) ** 2 + (self.lines[i][1] - local_pos[1]) ** 2,
        )

        self.lines.pop(hit_index)

        neighbor_indexes = []
        for offset in (-2, -1, 0, 1):
            neighbor_index = (hit_index + offset) % len(self.lines)
            if neighbor_index not in neighbor_indexes:
                neighbor_indexes.append(neighbor_index)

        for neighbor_index in neighbor_indexes:
            point = self.lines[neighbor_index]
            self.lines[neighbor_index] = (
                point[0] * (1 - inward_strength),
                point[1] * (1 - inward_strength),
            )

        return False

    def angle_between_points(self, a, b, c):
        ax, ay = a[0] - b[0], a[1] - b[1]
        cx, cy = c[0] - b[0], c[1] - b[1]

        angle_a = math.atan2(ay, ax)
        angle_c = math.atan2(cy, cx)

        angle = math.degrees(angle_c - angle_a)
        return angle % 360

    def get_axes(self, points):
        axes = []
        for i in range(len(points)):
            a = points[i]
            b = points[(i + 1) % len(points)]
            edge = (b[0] - a[0], b[1] - a[1])
            length = math.sqrt(edge[0] ** 2 + edge[1] ** 2)
            if length == 0:
                continue
            axes.append((-edge[1] / length, edge[0] / length))
        return axes

    def project(self, points, axis):
        dots = [p[0] * axis[0] + p[1] * axis[1] for p in points]
        return min(dots), max(dots)

    def get_mtv(self, poly_a, poly_b):
        axes = self.get_axes(poly_a) + self.get_axes(poly_b)
        min_overlap = float("inf")
        mtv_axis = None

        for axis in axes:
            min_a, max_a = self.project(poly_a, axis)
            min_b, max_b = self.project(poly_b, axis)

            overlap = min(max_a, max_b) - max(min_a, min_b)
            if overlap <= 0:
                return None

            if overlap < min_overlap:
                min_overlap = overlap
                mtv_axis = axis

        return min_overlap, mtv_axis

    def reflect_velocity(self, velocity, axis):
        dot = velocity[0] * axis[0] + velocity[1] * axis[1]
        return (
            velocity[0] - 2 * dot * axis[0],
            velocity[1] - 2 * dot * axis[1],
        )

    def elastic_collision(self, vel_a, mass_a, vel_b, mass_b, axis):
        a_dot = vel_a[0] * axis[0] + vel_a[1] * axis[1]
        b_dot = vel_b[0] * axis[0] + vel_b[1] * axis[1]

        new_a_dot = (a_dot * (mass_a - mass_b) + 2 * mass_b * b_dot) / (mass_a + mass_b)
        new_b_dot = (b_dot * (mass_b - mass_a) + 2 * mass_a * a_dot) / (mass_a + mass_b)

        delta_a = new_a_dot - a_dot
        delta_b = new_b_dot - b_dot

        new_vel_a = (
            vel_a[0] + delta_a * axis[0],
            vel_a[1] + delta_a * axis[1],
        )
        new_vel_b = (
            vel_b[0] + delta_b * axis[0],
            vel_b[1] + delta_b * axis[1],
        )

        return new_vel_a, new_vel_b

    def checkAsteroidCollision(self):
        my_points = self.get_world_points()

        for asteroid in Groups.asteroids:
            if asteroid is self or id(self) >= id(asteroid):
                continue

            if self.solarSystem is not None and asteroid.solarSystem is not None and self.solarSystem is not asteroid.solarSystem:
                continue

            max_distance = self.collisionRadius + asteroid.collisionRadius
            dx = self.pos[0] - asteroid.pos[0]
            dy = self.pos[1] - asteroid.pos[1]
            if dx * dx + dy * dy > max_distance * max_distance:
                continue

            other_points = asteroid.get_world_points()
            result = self.get_mtv(my_points, other_points)
            if result is None:
                continue

            overlap, axis = result
            if dx * axis[0] + dy * axis[1] < 0:
                axis = (-axis[0], -axis[1])

            total_mass = self.mass + asteroid.mass
            self.pos = (
                self.pos[0] + axis[0] * overlap * (asteroid.mass / total_mass),
                self.pos[1] + axis[1] * overlap * (asteroid.mass / total_mass),
            )
            asteroid.pos = (
                asteroid.pos[0] - axis[0] * overlap * (self.mass / total_mass),
                asteroid.pos[1] - axis[1] * overlap * (self.mass / total_mass),
            )

            self.velocity, asteroid.velocity = self.elastic_collision(
                self.velocity,
                self.mass,
                asteroid.velocity,
                asteroid.mass,
                axis,
            )
