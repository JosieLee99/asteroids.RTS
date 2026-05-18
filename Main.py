import math
import random

import pygame
from pygame.draw import lines

import Groups
from Asteroid import Asteroid
from ManageSolarSystems import ManageSolarSystem
from Player import Player
from Soldier import Soldier
from WriteWords import WriteWords

screen = Groups.screen
writer = WriteWords()

DEFAULT_CAMERA_ZOOM = 0.7
SELECTION_BOX_COLOR = (245, 65, 65)
MOVE_PREVIEW_COLOR = (245, 66, 66)
HUD_PADDING = 12
HUD_MARGIN = 20
HUD_TEXT_HEIGHT = 20
HUD_TEXT_SPACING = 4
SOLDIER_ATTACK_INTERVAL = 2.0

running = True
isLeftMouseButtonDown = False
startMousePosition = (0, 0)
attackTimer = 0.0
deltaTime = 1 / 60
clock = pygame.time.Clock()


def min_camera_zoom():
    return 0.11 * (Groups.actual_width / 1920)


def can_change_current_solar_system():
    mostly_zoomed_out = min_camera_zoom() + (DEFAULT_CAMERA_ZOOM - min_camera_zoom()) * 0.25
    return Groups.camera.zoom <= mostly_zoomed_out


def distance_squared(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def distance(a, b):
    return math.sqrt(distance_squared(a, b))


def find_solar_system_for_pos(pos):
    closest_solar_system = None
    closest_distance = float("inf")

    for solar_system in Groups.solarSystems:
        if Groups.camera.point_in_polygon(pos, solar_system.hexagonPoints):
            return solar_system

        solar_system_distance = distance_squared(pos, solar_system.pos)
        if solar_system_distance < closest_distance:
            closest_distance = solar_system_distance
            closest_solar_system = solar_system

    return closest_solar_system


def assign_solar_system(game_object):
    game_object.solarSystem = find_solar_system_for_pos(game_object.pos)


def get_solar_system_by_value(system_value):
    for solar_system in Groups.solarSystems:
        if solar_system.id == system_value:
            return solar_system
    return Groups.solarSystems.sprites()[0]


def solar_system_neighbor_limit():
    solar_systems = Groups.solarSystems.sprites()
    closest_distance = float("inf")

    for index, solar_system in enumerate(solar_systems):
        for other in solar_systems[index + 1:]:
            center_distance = distance(solar_system.pos, other.pos)
            if center_distance > 0:
                closest_distance = min(closest_distance, center_distance)

    if closest_distance == float("inf"):
        return 0

    return closest_distance * 1.1


def get_solar_system_neighbors(solar_system):
    neighbor_limit = solar_system_neighbor_limit()
    return [
        other
        for other in Groups.solarSystems
        if other is not solar_system and distance(solar_system.pos, other.pos) <= neighbor_limit
    ]


def reconstruct_solar_system_path(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def find_solar_system_path(start, goal):
    if start is None or goal is None:
        return []
    if start is goal:
        return [start]

    open_set = [start]
    came_from = {}
    g_score = {start: 0}
    f_score = {start: distance(start.pos, goal.pos)}

    while len(open_set) > 0:
        current = min(open_set, key=lambda solar_system: f_score.get(solar_system, float("inf")))
        if current is goal:
            return reconstruct_solar_system_path(came_from, current)

        open_set.remove(current)
        for neighbor in get_solar_system_neighbors(current):
            tentative_g_score = g_score[current] + distance(current.pos, neighbor.pos)
            if tentative_g_score < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + distance(neighbor.pos, goal.pos)
                if neighbor not in open_set:
                    open_set.append(neighbor)

    return []


def closest_edge_midpoint_to_point(solar_system, point):
    closest_midpoint = solar_system.pos
    closest_distance = float("inf")

    for index in range(len(solar_system.hexagonPoints)):
        a = solar_system.hexagonPoints[index]
        b = solar_system.hexagonPoints[(index + 1) % len(solar_system.hexagonPoints)]
        midpoint = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        midpoint_distance = distance_squared(midpoint, point)

        if midpoint_distance < closest_distance:
            closest_distance = midpoint_distance
            closest_midpoint = midpoint

    return closest_midpoint


def start_next_solar_system_transition(unit):
    if len(unit.solarSystemPath) == 0:
        unit.transitionTarget = None
        unit.transitionEntryPos = None
        unit.transitionSolarSystem = None
        if unit.finalDestinationPos is not None:
            unit.destinationPos = unit.finalDestinationPos
        return

    next_solar_system = unit.solarSystemPath.pop(0)
    unit.transitionSolarSystem = next_solar_system
    unit.transitionTarget = closest_edge_midpoint_to_point(unit.solarSystem, next_solar_system.pos)
    unit.transitionEntryPos = closest_edge_midpoint_to_point(next_solar_system, unit.solarSystem.pos)
    unit.destinationPos = unit.transitionTarget


def set_unit_destination(unit, destination_pos):
    unit.interactableTarget = None
    if unit.solarSystem is None:
        assign_solar_system(unit)

    destination_solar_system = find_solar_system_for_pos(destination_pos)
    unit.finalDestinationPos = destination_pos

    if unit.solarSystem is destination_solar_system:
        unit.destinationPos = destination_pos
        unit.solarSystemPath = []
        unit.transitionTarget = None
        unit.transitionEntryPos = None
        unit.transitionSolarSystem = None
        return

    path = find_solar_system_path(unit.solarSystem, destination_solar_system)
    if len(path) <= 1:
        unit.destinationPos = destination_pos
        return

    unit.solarSystemPath = path[1:]
    start_next_solar_system_transition(unit)


def update_unit_solar_system_transition(unit):
    if unit.transitionTarget is None:
        return

    if distance(unit.pos, unit.transitionTarget) > 45:
        return

    unit.pos = unit.transitionEntryPos
    unit.velocity = (0, 0)
    unit.solarSystem = unit.transitionSolarSystem
    unit.transitionTarget = None
    unit.transitionEntryPos = None
    unit.transitionSolarSystem = None

    if len(unit.solarSystemPath) > 0:
        start_next_solar_system_transition(unit)
    elif unit.finalDestinationPos is not None:
        unit.destinationPos = unit.finalDestinationPos


def top_solar_system():
    if len(Groups.solarSystems) == 0:
        return None
    return min(Groups.solarSystems, key=lambda solar_system: solar_system.pos[1])


def bottom_solar_system():
    if len(Groups.solarSystems) == 0:
        return None
    return max(Groups.solarSystems, key=lambda solar_system: solar_system.pos[1])


def team_home_solar_system(team):
    if team == 1:
        return bottom_solar_system()
    if team == 2:
        return top_solar_system()
    return get_solar_system_by_value(Groups.currentSolarSystemID)


def spawn_pos_for_team(team):
    home_solar_system = team_home_solar_system(team)
    if home_solar_system is None:
        return random_world_pos()
    return home_solar_system.pos


def spawn_player(team):
    spawn_pos = spawn_pos_for_team(team)
    player = Player(
        screen,
        team,
        10,
        [],
        spawn_pos,
        spawn_pos,
        (0, 0),
        0,
    )
    player.solarSystem = team_home_solar_system(team)
    return player


def spawn_soldier(team):
    spawn_pos = spawn_pos_for_team(team)
    soldier = Soldier(
        screen,
        team,
        10,
        [],
        spawn_pos,
        spawn_pos,
        (0, 0),
        0,
        None,
    )
    soldier.solarSystem = team_home_solar_system(team)
    return soldier


def spawn_asteroid():
    asteroid = Asteroid(screen, random.randint(5, 10), lines, random_world_pos((100, 400)), (0, 0), 0)
    assign_solar_system(asteroid)
    return asteroid


def random_world_pos(x_range=(-300, 300), y_range=(-200, 200)):
    return (random.randint(*x_range), random.randint(*y_range))


def selectable_units():
    return list(Groups.players) + list(Groups.soldiers)


def get_world_click():
    return Groups.camera.screen_to_world(pygame.mouse.get_pos())


def get_start_screen():
    return (
        int((startMousePosition[0] - Groups.camera.pos[0]) * Groups.camera.zoom + Groups.camera.width / 2),
        int((startMousePosition[1] - Groups.camera.pos[1]) * Groups.camera.zoom + Groups.camera.height / 2),
    )


def drag_box_bounds():
    start_screen = get_start_screen()
    current_mouse = pygame.mouse.get_pos()
    return (
        min(start_screen[0], current_mouse[0]),
        max(start_screen[0], current_mouse[0]),
        min(start_screen[1], current_mouse[1]),
        max(start_screen[1], current_mouse[1]),
    )


def point_in_drag_box(point):
    min_x, max_x, min_y, max_y = drag_box_bounds()
    return min_x <= point[0] <= max_x and min_y <= point[1] <= max_y


def update_camera(mouse_offset):
    if Groups.camera.zoom <= min_camera_zoom():
        Groups.camera.zoom = min_camera_zoom()

    focal = get_solar_system_by_value(Groups.currentSolarSystemID).pos
    Groups.camera.pos = (focal[0] + mouse_offset[0], focal[1] + mouse_offset[1])


def try_change_current_solar_system(world_click):
    if not can_change_current_solar_system():
        return False

    for solar_system in Groups.solarSystems:
        if Groups.camera.point_in_polygon(world_click, solar_system.hexagonPoints):
            Groups.currentSolarSystemID = solar_system.id
            return True

    return False


def find_clicked_asteroid(world_click):
    for asteroid in Groups.asteroids:
        asteroid_points = [(point[0] + asteroid.pos[0], point[1] + asteroid.pos[1]) for point in asteroid.lines]
        if Groups.camera.point_in_polygon(world_click, asteroid_points):
            return asteroid
    return None


def handle_left_mouse_down():
    global isLeftMouseButtonDown, startMousePosition

    world_click = get_world_click()
    clicked_solar_system = try_change_current_solar_system(world_click)
    startMousePosition = world_click
    isLeftMouseButtonDown = not clicked_solar_system


def handle_right_mouse_down():
    world_click = get_world_click()
    clicked_asteroid = find_clicked_asteroid(world_click)

    if clicked_asteroid is not None:
        for unit in Groups.selectedSoldiers:
            if unit in Groups.soldiers:
                unit.interactableTarget = clicked_asteroid
                unit.target = clicked_asteroid.pos
                unit.solarSystemPath = []
                unit.transitionTarget = None
                unit.transitionEntryPos = None
                unit.transitionSolarSystem = None
        return

    for index, unit in enumerate(Groups.selectedSoldiers):
        unit_screen_pos = unit.world_to_screen(unit.pos, Groups.camera.pos, Groups.camera.zoom)
        pygame.draw.line(screen, MOVE_PREVIEW_COLOR, unit_screen_pos, pygame.mouse.get_pos(), 1)

        if index == 0:
            set_unit_destination(unit, world_click)
        else:
            set_unit_destination(
                unit,
                (world_click[0] + random.randint(-100, 100), world_click[1] + random.randint(-100, 100)),
            )


def handle_left_mouse_up():
    global isLeftMouseButtonDown

    if not isLeftMouseButtonDown:
        return

    Groups.selectedSoldiers.empty()
    for unit in selectable_units():
        unit_screen_pos = unit.world_to_screen(unit.pos, Groups.camera.pos, Groups.camera.zoom)
        if point_in_drag_box(unit_screen_pos):
            Groups.selectedSoldiers.add(unit)

    isLeftMouseButtonDown = False


def handle_keydown(event):
    if event.key == pygame.K_1:
        spawn_player(1)
    if event.key == pygame.K_2:
        spawn_player(2)
    if event.key == pygame.K_3:
        spawn_soldier(1)
    if event.key == pygame.K_4:
        spawn_soldier(2)
    if event.key == pygame.K_0:
        spawn_asteroid()


def draw_selection_box():
    if not isLeftMouseButtonDown:
        return

    start_screen = get_start_screen()
    current_mouse = pygame.mouse.get_pos()
    if current_mouse == start_screen:
        return

    points = [
        start_screen,
        (current_mouse[0], start_screen[1]),
        current_mouse,
        (start_screen[0], current_mouse[1]),
    ]
    pygame.draw.lines(screen, SELECTION_BOX_COLOR, True, points, 1)


def update_player_units():
    for player in Groups.players:
        player.spawnPlayerVector()
        player.setPosition()
        player.move()
        player_world_points = player.get_player_points()

        if len(Groups.solarSystems) > 0:
            if player.solarSystem is None:
                assign_solar_system(player)
            solar_system = player.solarSystem
            player.pos, player.velocity = solar_system.confine_to_hexagon(
                (player.pos[0], player.pos[1]),
                player_world_points,
                (player.velocity[0], player.velocity[1]),
            )
            update_unit_solar_system_transition(player)


def update_soldier_units(delta_time):
    global attackTimer

    for soldier in Groups.soldiers:
        soldier.updateCombatTarget()
        soldier.spawnPawnVector()
        soldier.setPosition()
        soldier.move()
        soldier_world_points = soldier.get_pawn_points()

        if len(Groups.solarSystems) > 0:
            if soldier.solarSystem is None:
                assign_solar_system(soldier)
            solar_system = soldier.solarSystem
            soldier.pos, soldier.velocity = solar_system.confine_to_hexagon(
                (soldier.pos[0], soldier.pos[1]),
                soldier_world_points,
                (soldier.velocity[0], soldier.velocity[1]),
            )
            update_unit_solar_system_transition(soldier)

    attackTimer += delta_time
    if attackTimer >= SOLDIER_ATTACK_INTERVAL:
        attackTimer = 0.0
        for soldier in list(Groups.soldiers):
            soldier.attackTarget()


def update_asteroid_units():
    for asteroid in Groups.asteroids:
        asteroid.spawnAsteroidVector()
        asteroid.setPosition()
        asteroid_world_points = [(point[0] + asteroid.pos[0], point[1] + asteroid.pos[1]) for point in asteroid.lines]

        if len(Groups.solarSystems) > 0:
            if asteroid.solarSystem is None:
                assign_solar_system(asteroid)
            solar_system = asteroid.solarSystem
            asteroid.pos, asteroid.velocity = solar_system.confine_to_hexagon(
                (asteroid.pos[0], asteroid.pos[1]),
                asteroid_world_points,
                (asteroid.velocity[0], asteroid.velocity[1]),
            )


def draw_solar_systems():
    solar_systems = Groups.solarSystems.sprites()
    if len(solar_systems) > 0:
        solar_systems[0].draw(screen)


def draw_hud():
    draw_hud_box(
        "METALS " + str(Groups.camera.metals),
        Groups.team_color(1),
        align_right=True,
    )
    draw_hud_box(
        str(Groups.camera.metals) + " METALS",
        Groups.team_color(2),
        align_right=False,
    )


def draw_hud_box(text, color, align_right):
    text_width, text_height = writer.measure_text(text, HUD_TEXT_HEIGHT, HUD_TEXT_SPACING)

    if align_right:
        x = Groups.camera.width - text_width - HUD_PADDING * 2 - HUD_MARGIN
    else:
        x = HUD_MARGIN

    text_box = pygame.Rect(
        x,
        Groups.camera.height - text_height - HUD_PADDING * 2 - HUD_MARGIN,
        text_width + HUD_PADDING * 2,
        text_height + HUD_PADDING * 2,
    )

    pygame.draw.rect(screen, (0, 0, 0), text_box)
    pygame.draw.rect(screen, color, text_box, 2)
    writer.draw_text(
        screen,
        text,
        (text_box.x + HUD_PADDING, text_box.y + HUD_PADDING),
        color=color,
        height=HUD_TEXT_HEIGHT,
        spacing=HUD_TEXT_SPACING,
    )


mapManager = ManageSolarSystem()
mapManager.spawnBigMap(1500, 50)
Groups.currentSolarSystemID = bottom_solar_system().id

spawn_soldier(1)
spawn_player(1)

while running:
    screen.fill((0, 0, 0))

    mouse = pygame.mouse.get_pos()
    mouse_offset = (
        (mouse[0] - Groups.camera.width / 2) * 0.3,
        (mouse[1] - Groups.camera.height / 2) * 0.3,
    )
    update_camera(mouse_offset)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == pygame.BUTTON_LEFT:
                handle_left_mouse_down()
            if event.button == pygame.BUTTON_RIGHT:
                handle_right_mouse_down()
            if event.button == pygame.BUTTON_WHEELUP:
                Groups.camera.zoom *= 1.2
            if event.button == pygame.BUTTON_WHEELDOWN:
                Groups.camera.zoom = max(min_camera_zoom(), Groups.camera.zoom * 0.8)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == pygame.BUTTON_LEFT:
                handle_left_mouse_up()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            else:
                handle_keydown(event)

    draw_selection_box()
    update_player_units()
    update_soldier_units(deltaTime)
    update_asteroid_units()
    draw_solar_systems()
    draw_hud()

    pygame.display.flip()
    deltaTime = clock.tick(60) / 1000
    deltaTime = max(0.001, min(0.1, deltaTime))

pygame.quit()
