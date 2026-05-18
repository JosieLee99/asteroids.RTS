import random

import pygame
import math

import Groups


class Soldier(pygame.sprite.Sprite):
    def __init__(self, screen, team, points, lines, pos, destinationPos, velocity, rot, target):
        super().__init__()
        Groups.soldiers.add(self)
        rot = 0

        self.mass = 30
        self.team = team
        self.shouldMove = False
        self.isInit = True
        self.screen = screen
        self.pos = pos
        self.destinationPos = destinationPos
        self.target = self.destinationPos
        self.interactableTarget = None
        self.solarSystem = None
        self.solarSystemPath = []
        self.finalDestinationPos = None
        self.transitionTarget = None
        self.transitionEntryPos = None
        self.transitionSolarSystem = None
        self.velocity = velocity
        self.rot = rot
        self.lines = lines
        self.health = 100
        self.attackRadius = 450
        self.attackDamage = 5
        self.acceleration = 0.15
        self.maxVelocity = 8
        self.collisionRadius = 35

    def spawnPawnVector(self):
        self.lines = self.get_pawn_points()
        self.target = self.destinationPos if self.interactableTarget is None else self.interactableTarget.pos
        postRotatedPoints = self.rotate_points(
            self.lines,
            self.pos,
            self.angle_between_points((self.pos[0], self.pos[1] + 1), self.pos, self.target),
        )

        screen_points = [self.world_to_screen(p, Groups.camera.pos, Groups.camera.zoom) for p in postRotatedPoints]

        pygame.draw.lines(self.screen, Groups.team_color(self.team), True, screen_points, 2)

        self.checkAsteroidCollision()
        self.checkForDestinationCollision()

    def updateCombatTarget(self):
        closest_enemy = None
        closest_distance = self.attackRadius ** 2

        possible_targets = list(Groups.soldiers) + list(Groups.players)
        for target in possible_targets:
            if target is self or target.team == self.team:
                continue

            distance = (self.pos[0] - target.pos[0]) ** 2 + (self.pos[1] - target.pos[1]) ** 2
            if distance <= closest_distance:
                closest_distance = distance
                closest_enemy = target

        if closest_enemy is not None:
            self.interactableTarget = closest_enemy
            self.target = closest_enemy.pos
        elif self.isCombatTarget(self.interactableTarget):
            self.interactableTarget = None
            self.target = self.destinationPos

    def get_pawn_points(self):
        return [
            (20 + self.pos[0], self.pos[1] + 4),
            (10 + self.pos[0], self.pos[1]),
            (-10 + self.pos[0], self.pos[1]),
            (-20 + self.pos[0], self.pos[1] + 4),
            (self.pos[0], self.pos[1] - 20)
        ]

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

        if self.rot > 360:
            self.rot -= 360
        elif self.rot < -360:
            self.rot += 360

        return rotated

    def angle_between_points(self, a, b, c):
        ax, ay = a[0] - b[0], a[1] - b[1]
        cx, cy = c[0] - b[0], c[1] - b[1]

        angle_a = math.atan2(ay, ax)
        angle_c = math.atan2(cy, cx)

        angle = math.degrees(angle_c - angle_a)
        return angle % 360

    def setPosition(self):
        self.pos = list(self.pos)
        self.pos[0] += self.velocity[0]
        self.pos[1] -= self.velocity[1]
        self.pos = tuple(self.pos)

    def setRotation(self, rotation):
        self.rot += rotation
        if self.rot > 360:
            self.rot -= 360

    def attackTarget(self):
        if self.interactableTarget is not None:
            if self.isCombatTarget(self.interactableTarget):
                self.attackCombatTarget(self.interactableTarget)
                return

            if self.interactableTarget in Groups.asteroids:
                self.attackAsteroid(self.interactableTarget)
                return

            self.interactableTarget = None
            self.target = self.destinationPos

    def isCombatTarget(self, target):
        return target in Groups.soldiers or target in Groups.players

    def attackCombatTarget(self, target):
        soldier_screen_pos = self.world_to_screen(self.pos, Groups.camera.pos, Groups.camera.zoom)
        target_screen_pos = self.world_to_screen(target.pos, Groups.camera.pos, Groups.camera.zoom)
        pygame.draw.line(self.screen, Groups.team_color(self.team), soldier_screen_pos, target_screen_pos, 2)

        target.health -= self.attackDamage
        if target.health <= 0:
            target.health = 0
            target.kill()
            if target in Groups.selectedSoldiers:
                Groups.selectedSoldiers.remove(target)
            self.interactableTarget = None
            self.target = self.destinationPos

    def attackAsteroid(self, asteroid):
        Groups.camera.metals += 1
        soldier_screen_pos = self.world_to_screen(self.pos, Groups.camera.pos, Groups.camera.zoom)
        asteroid_point = self.closest_point_on_asteroid(asteroid)
        asteroid_screen_pos = self.world_to_screen(asteroid_point, Groups.camera.pos, Groups.camera.zoom)
        pygame.draw.line(self.screen, Groups.team_color(self.team), soldier_screen_pos, asteroid_screen_pos, 2)
        asteroid_destroyed = asteroid.remove_point_near_world_pos(asteroid_point)
        if asteroid_destroyed:
            self.interactableTarget = None
            self.target = self.destinationPos
            return

        asteroid.health -= self.attackDamage

        if asteroid.health <= 0:
            asteroid.health = 0

    def closest_point_on_asteroid(self, asteroid):
        asteroid_points = [(p[0] + asteroid.pos[0], p[1] + asteroid.pos[1]) for p in asteroid.lines]
        closest_point = asteroid_points[0]
        closest_distance = float('inf')

        for i in range(len(asteroid_points)):
            a = asteroid_points[i]
            b = asteroid_points[(i + 1) % len(asteroid_points)]
            point = self.closest_point_on_segment(self.pos, a, b)
            distance = (self.pos[0] - point[0]) ** 2 + (self.pos[1] - point[1]) ** 2

            if distance < closest_distance:
                closest_distance = distance
                closest_point = point

        return closest_point

    def closest_point_on_segment(self, point, a, b):
        ax, ay = a
        bx, by = b
        px, py = point
        segment_x = bx - ax
        segment_y = by - ay
        segment_length = segment_x ** 2 + segment_y ** 2

        if segment_length == 0:
            return a

        t = ((px - ax) * segment_x + (py - ay) * segment_y) / segment_length
        t = max(0, min(1, t))

        return (ax + t * segment_x, ay + t * segment_y)

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
                # Reflect velocity off this wall
                vel_dot = self.velocity[0] * inward[0] + self.velocity[1] * inward[1]
                if vel_dot < 0:
                    self.velocity = (
                        self.velocity[0] - 2 * vel_dot * inward[0],
                        self.velocity[1] - 2 * vel_dot * inward[1]
                    )

    def scale_points(self, center, scale):
        """
        Scales a list of points toward/away from a center point.
        scale > 1 = zoom in, scale < 1 = zoom out
        """
        cx, cy = pygame.mouse.get_pos()
        return [
            (cx + (p[0] - cx) * scale, cy + (p[1] - cy) * scale)
            for p in self.lines
        ]

    def world_to_screen(self, point, camera_pos, zoom):
        """Convert a world position to screen position with zoom."""
        cx, cy = camera_pos
        return (
            (point[0] - cx) * zoom + Groups.camera.width / 2,
            (point[1] - cy) * zoom + Groups.camera.height / 2
        )

    def checkForDestinationCollision(self):
        for asteroid in Groups.asteroids:
            if self.solarSystem is not None and asteroid.solarSystem is not None and asteroid.solarSystem is not self.solarSystem:
                continue

            # Offset the destination by the asteroid's position to match local space
            local_dest = (
                self.destinationPos[0] - asteroid.pos[0],
                self.destinationPos[1] - asteroid.pos[1]
            )
            if self.point_in_bbox(local_dest, asteroid.lines):
                self.destinationPos = (
                    self.destinationPos[0] + random.randint(-200, 200),
                    self.destinationPos[1] + random.randint(-200, 200)
                )

    def point_in_bbox(self, point, poly_points):
        xs = [p[0] for p in poly_points]
        ys = [p[1] for p in poly_points]
        return min(xs) <= point[0] <= max(xs) and min(ys) <= point[1] <= max(ys)

    def move(self):
        accel = self.acceleration

        if self.pos[1] < self.destinationPos[1] - 20:
            self.velocity = list(self.velocity)
            if self.velocity[1] < 0:
                self.velocity[1] *= 0.99
            self.velocity[1] -= accel
            if self.velocity[1] < -self.maxVelocity:
                self.velocity[1] = -self.maxVelocity
            self.velocity = tuple(self.velocity)

        if self.pos[1] > self.destinationPos[1] + 20:
            self.velocity = list(self.velocity)
            if self.velocity[1] > 0:
                self.velocity[1] *= 0.99
            self.velocity[1] += accel
            if self.velocity[1] > self.maxVelocity:
                self.velocity[1] = self.maxVelocity
            self.velocity = tuple(self.velocity)

        if self.pos[0] > self.destinationPos[0] + 20:
            self.velocity = list(self.velocity)
            if self.velocity[0] > 0:
                self.velocity[0] *= 0.99
            self.velocity[0] -= accel
            if self.velocity[0] < -self.maxVelocity:
                self.velocity[0] = -self.maxVelocity
            self.velocity = tuple(self.velocity)

        if self.pos[0] < self.destinationPos[0] - 20:
            self.velocity = list(self.velocity)
            if self.velocity[0] < 0:
                self.velocity[0] *= 0.99
            self.velocity[0] += accel
            if self.velocity[0] > self.maxVelocity:
                self.velocity[0] = self.maxVelocity
            self.velocity = tuple(self.velocity)

        self.clamp_velocity()

    def clamp_velocity(self):
        speed = math.sqrt(self.velocity[0] ** 2 + self.velocity[1] ** 2)
        if speed <= self.maxVelocity or speed == 0:
            return

        scale = self.maxVelocity / speed
        self.velocity = (
            self.velocity[0] * scale,
            self.velocity[1] * scale
        )

    def get_axes(self, points):
        axes = []
        for i in range(len(points)):
            a = points[i]
            b = points[(i + 1) % len(points)]
            edge = (b[0] - a[0], b[1] - a[1])
            length = math.sqrt(edge[0] ** 2 + edge[1] ** 2)
            if length == 0:
                continue
            # Normalized perpendicular normal
            normal = (-edge[1] / length, edge[0] / length)
            axes.append(normal)
        return axes

    def project(self, points, axis):
        dots = [p[0] * axis[0] + p[1] * axis[1] for p in points]
        return min(dots), max(dots)

    def get_mtv(self, poly_a, poly_b):
        """
        Returns (overlap, normal) as the minimum translation vector
        to push poly_a out of poly_b, or None if no collision.
        """
        axes = self.get_axes(poly_a) + self.get_axes(poly_b)
        min_overlap = float('inf')
        mtv_axis = None

        for axis in axes:
            min_a, max_a = self.project(poly_a, axis)
            min_b, max_b = self.project(poly_b, axis)

            overlap = min(max_a, max_b) - max(min_a, min_b)

            if overlap <= 0:
                return None  # gap found, no collision

            if overlap < min_overlap:
                min_overlap = overlap
                mtv_axis = axis

        return min_overlap, mtv_axis

    def checkAsteroidCollision(self):
        soldier_points = self.rotate_points(
            self.lines, self.pos,
            self.angle_between_points((self.pos[0], self.pos[1] + 1), self.pos, self.target)
        )

        for asteroid in Groups.asteroids:
            if self.solarSystem is not None and asteroid.solarSystem is not None and asteroid.solarSystem is not self.solarSystem:
                continue

            max_distance = self.collisionRadius + asteroid.collisionRadius
            dx = self.pos[0] - asteroid.pos[0]
            dy = self.pos[1] - asteroid.pos[1]
            if dx * dx + dy * dy > max_distance * max_distance:
                continue

            asteroid_points = asteroid.get_world_points()

            result = self.get_mtv(soldier_points, asteroid_points)
            if result is None:
                continue

            overlap, axis = result
            if dx * axis[0] + dy * axis[1] < 0:
                axis = (-axis[0], -axis[1])

            total_mass = self.mass + asteroid.mass

            # Push out weighted by mass
            self.pos = (
                self.pos[0] + axis[0] * overlap * (asteroid.mass / total_mass),
                self.pos[1] + axis[1] * overlap * (asteroid.mass / total_mass)
            )
            asteroid.pos = (
                asteroid.pos[0] - axis[0] * overlap * (self.mass / total_mass),
                asteroid.pos[1] - axis[1] * overlap * (self.mass / total_mass)
            )

            # Apply elastic collision
            self.velocity, asteroid.velocity = self.elastic_collision(
                self.velocity, self.mass,
                asteroid.velocity, asteroid.mass,
                axis
            )

    def reflect_velocity(self, velocity, axis):
        """Reflect a velocity vector along a collision normal."""
        dot = velocity[0] * axis[0] + velocity[1] * axis[1]
        return (
            velocity[0] - 2 * dot * axis[0],
            velocity[1] - 2 * dot * axis[1]
        )

    def elastic_collision(self, vel_a, mass_a, vel_b, mass_b, axis):
        """
        Resolves an elastic collision between two objects along a collision axis.
        Returns new (vel_a, vel_b) after collision.
        Zero gravity — no dampening, energy is fully conserved.
        """
        # Project velocities onto collision axis
        a_dot = vel_a[0] * axis[0] + vel_a[1] * axis[1]
        b_dot = vel_b[0] * axis[0] + vel_b[1] * axis[1]

        # 1D elastic collision formula along the axis
        new_a_dot = (a_dot * (mass_a - mass_b) + 2 * mass_b * b_dot) / (mass_a + mass_b)
        new_b_dot = (b_dot * (mass_b - mass_a) + 2 * mass_a * a_dot) / (mass_a + mass_b)

        # Delta to apply back to full 2D velocity
        delta_a = new_a_dot - a_dot
        delta_b = new_b_dot - b_dot

        new_vel_a = (
            vel_a[0] + delta_a * axis[0],
            vel_a[1] + delta_a * axis[1]
        )
        new_vel_b = (
            vel_b[0] + delta_b * axis[0],
            vel_b[1] + delta_b * axis[1]
        )

        return new_vel_a, new_vel_b


