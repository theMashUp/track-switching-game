# -*- coding: utf-8 -*-

# import built-in module
import math

# import third-party modules
import pygame as pg
from pygame import Vector2

# import your own module
from trackswitchinggame.wagonsprite import WagonSprite
from trackswitchinggame.levelmap import LevelMap
from trackswitchinggame.constants import *


class Train:
    """
    Represents a self-contained train, which is composed of wagons.
    A train spawns at a given entry_portal, will wait at a platform and despawn at an exit portal.
    Specific platform and exit_portal are provided as a goal to the player, but the train will wait at any platform,
    and despawn at any portal it crosses.
    The train's movement follow points stored in trajectory.
    """

    WAIT_DELAY_VS_SPEED = {1: 5000,
                           2: 4000,
                           3: 3000,
                           4: 2000,
                           5: 1000}

    def __init__(self, levelmap: LevelMap, entry_portal: str, platform: str, exit_portal: str):
        self._levelmap = levelmap
        self.trajectory = list()
        self.rightmost_position_pointer = None  # Initialized when calling spawn()
        self.speed = 1

        # Set-up wagons
        self._wagons = pg.sprite.Group()
        self._wagons.add(WagonSprite("assets/trains/ice_loc.png"))
        self._wagons.add(WagonSprite("assets/trains/ice_wagon.png"))
        self._wagons.add(WagonSprite("assets/trains/ice_loc.png", True))

        # Goals
        self._entry_portal = entry_portal
        self._platform = platform
        self._platform_status = PENDING
        self._exit_portal = exit_portal
        self._exit_portal_status = PENDING

        # State variables
        self._spawned = False
        self._moving = False
        self._waiting = False
        self.direction = None
        self._wait_end = 0
        self._wait_total = 0

        # Indicators
        self._GOAL_INDICATOR_SIZE = 10
        self._WAIT_INDICATOR_SIZE = 14
        self._font = pg.font.SysFont("Verdana", self._GOAL_INDICATOR_SIZE)

        # Prepare trajectory for the spawn
        portal_tile = self._levelmap.portals[self._entry_portal].sprites()[0]
        spawn_tile_traj = portal_tile.get_trajectory()
        nb_padding_tiles = math.ceil(self.length / TILE_LENGTH)
        if (portal_tile.get_neighbour(NW) is None) and \
                (portal_tile.get_neighbour(W) is None) and \
                (portal_tile.get_neighbour(SW) is None):
            for i in range(nb_padding_tiles * TILE_LENGTH):
                self.trajectory.append(Vector2(-(nb_padding_tiles * TILE_LENGTH) + i, spawn_tile_traj[0].y))
            self.trajectory += spawn_tile_traj
            self.direction = FORWARD
            self.rightmost_position_pointer = len(self.trajectory) - 1
        elif (portal_tile.get_neighbour(NE) is None) and \
                (portal_tile.get_neighbour(E) is None) and \
                (portal_tile.get_neighbour(SE) is None):
            self.trajectory += spawn_tile_traj
            for i in range(nb_padding_tiles * TILE_LENGTH):
                self.trajectory.append(Vector2(spawn_tile_traj[-1].x + i, spawn_tile_traj[0].y))
            self.direction = BACKWARD
            self.leftmost_position_pointer = 0

    def update(self):
        """
        Update position of the train
        """
        if self._platform_status == PENDING:
            self._check_for_platform()
        elif self._exit_portal_status == PENDING:
            self._check_for_exit_portal()

        if self.moving:
            # Update position
            self._update_trajectory()
            self.rightmost_position_pointer += self.trajectory_pointer_increment
            if self.rightmost_position_pointer >= len(self.trajectory) or self.leftmost_position_pointer < 0:
                # No trajectory defined, we do not move.
                self.rightmost_position_pointer -= self.trajectory_pointer_increment
            else:
                current_offset = self.rightmost_position_pointer

                for wagon in self._wagons.sprites():
                    # Should the position of the axles be handled individually by each wagon?
                    # Do we want wagons to have a variable axle offset??
                    axle_1_pointer = current_offset - 5
                    axle_2_pointer = current_offset - 24
                    position_axle_1 = self.trajectory[axle_1_pointer]
                    position_axle_2 = self.trajectory[axle_2_pointer]
                    wagon.update(position_axle_1, position_axle_2)
                    current_offset -= wagon.length
                    wagon.rect.x = self.trajectory[current_offset + 1].x

        if self.waiting:
            if pg.time.get_ticks() > self._wait_end:
                self._waiting = False
                self.start(self.direction)

    def draw(self, screen: pg.surface.Surface):
        """
        Draw the train.
        """
        if self.spawned:
            # Draw wagons
            self._wagons.draw(screen)

            # Draw current goal on first front-facing wagon
            goal_indicator = pg.surface.Surface((self._GOAL_INDICATOR_SIZE, self._GOAL_INDICATOR_SIZE))

            if self._platform_status == PENDING:
                goal_indicator.fill(pg.Color("lightgreen"))
                goal_indicator.blit(self._font.render(self._platform, True, pg.Color("black")),
                                    (3, 1))
            elif self._exit_portal_status == PENDING:
                goal_indicator.fill(pg.Color("lightblue"))
                goal_indicator.blit(self._font.render(self._exit_portal, True, pg.Color("black")),
                                    (3, 1))
            else:
                goal_indicator.set_alpha(0)

            goal_indicator_rect = goal_indicator.get_rect()
            if self.direction == FORWARD:
                first_wagon = self._wagons.sprites()[0]
            elif self.direction == BACKWARD:
                first_wagon = self._wagons.sprites()[-1]
            goal_indicator_rect.center = first_wagon.rect.center

            screen.blit(goal_indicator, goal_indicator_rect)

            if self.waiting:
                # Draw wait indicator in front of train
                wait_indicator = pg.Surface((self._WAIT_INDICATOR_SIZE, self._WAIT_INDICATOR_SIZE))
                wait_indicator.fill(pg.Color("white"))
                wait_indicator.set_colorkey(pg.Color("white"))
                pg.draw.arc(wait_indicator, pg.Color("darkorange"), wait_indicator.get_rect(),
                            0, (self._wait_end - pg.time.get_ticks()) / self._wait_total * 2 * math.pi,
                            2)
                wait_indicator_rect = wait_indicator.get_rect()
                if self.direction == FORWARD:
                    wait_indicator_rect.center = self._wagons.sprites()[0].rect.center + Vector2(TILE_LENGTH, 0)
                elif self.direction == BACKWARD:
                    wait_indicator_rect.center = self._wagons.sprites()[-1].rect.center - Vector2(TILE_LENGTH, 0)
                screen.blit(wait_indicator, wait_indicator_rect)

    def start(self, direction: str):
        """
        Sets train in movement in desired direction.
        """
        if not self.waiting:
            self.direction = direction
            self._moving = True

    def stop(self):
        """
        Train stops.
        """
        self._moving = False

    def spawn(self):
        """
        Spawn train.
        """
        self._spawned = True
        self.start(self.direction)
        self.wait(self.WAIT_DELAY_VS_SPEED[self.speed])

        # This update allows the train to appear at the right position, even though it is currently waiting.
        current_offset = self.rightmost_position_pointer
        for wagon in self._wagons.sprites():
            # Should the position of the axles be handled individually by each wagon?
            # Do we want wagons to have a variable axle offset??
            axle_1_pointer = current_offset - 5
            axle_2_pointer = current_offset - 24
            position_axle_1 = self.trajectory[axle_1_pointer]
            position_axle_2 = self.trajectory[axle_2_pointer]
            wagon.update(position_axle_1, position_axle_2)
            current_offset -= wagon.length

    def despawn(self):
        """
        Despawn train.
        """
        self._spawned = False
        self.stop()

    def wait(self, milliseconds: int):
        """
        Wait for number of milliseconds.
        """
        self._wait_end = pg.time.get_ticks() + milliseconds
        self._wait_total = milliseconds
        self.stop()
        self._waiting = True

    def colliderect(self, rect: pg.Rect) -> bool:
        """
        Checks if the train collides a Rect.
        """
        for point in self.trajectory[self.leftmost_position_pointer:self.rightmost_position_pointer]:
            if rect.collidepoint(point.x, point.y):
                return True
        return False

    def _check_for_platform(self):
        for platform, group in self._levelmap.platforms.items():
            rect = None
            for sprite in group:
                if not rect:
                    rect = sprite.rect
                else:
                    rect = rect.union(sprite.rect)
            if rect.contains(self.rect):
                self.wait(self.WAIT_DELAY_VS_SPEED[self.speed])

                # Change direction based on exit goal
                train_position = self.trajectory[self.leftmost_position_pointer]
                exit_portal_position = Vector2(self._levelmap.portals[self._exit_portal].sprites()[0].rect.center)
                if train_position.x - exit_portal_position.x > 0:
                    self.direction = BACKWARD
                else:
                    self.direction = FORWARD

                # Check if platform goal was successful or not
                if self._platform == platform:
                    self._platform_status = SUCCEEDED
                else:
                    self._platform_status = FAILED
                break

    def _check_for_exit_portal(self):
        for portal, group in self._levelmap.portals.items():
            tile = group.sprites()[0]
            if self.rect.colliderect(tile.rect):
                if tile.portal == self._exit_portal:
                    self._exit_portal_status = SUCCEEDED
                else:
                    self._exit_portal_status = FAILED
                break

    def _update_trajectory(self):
        if self.direction == FORWARD:
            if (self.rightmost_position_pointer + self.trajectory_pointer_increment) >= len(self.trajectory):
                # We need to fetch trajectory information from next tile
                train_vector = self.trajectory[-1] - self.trajectory[-2]
                next_tile_position = self.trajectory[-1] + train_vector
                next_tile = self._levelmap.tile_at(next_tile_position)
                if next_tile:
                    new_trajectory = next_tile.get_trajectory()
                    # Check if our entry point is valid for the next tile
                    if next_tile_position in new_trajectory:
                        self.trajectory += new_trajectory
                else:
                    # No next tile, which means we are headed out of playing field.
                    # Padding with a straight trajectory for now.
                    last_point = self.trajectory[-1]
                    self.trajectory += [last_point + Vector2(i, 0) for i in range(TILE_LENGTH)]

            if (self.leftmost_position_pointer + self.trajectory_pointer_increment) >= TILE_LENGTH:
                # We can delete trajectory information from last tile
                self.trajectory = self.trajectory[TILE_LENGTH:]
                self.rightmost_position_pointer -= TILE_LENGTH

        elif self.direction == BACKWARD:
            if (self.leftmost_position_pointer + self.trajectory_pointer_increment) < 0:
                # We need to fetch trajectory information from previous tile
                train_vector = self.trajectory[0] - self.trajectory[1]
                next_tile_position = self.trajectory[0] + train_vector
                next_tile = self._levelmap.tile_at(next_tile_position)
                if next_tile:
                    new_trajectory = next_tile.get_trajectory()
                    # Check if our entry point is valid for the next tile
                    if next_tile_position in new_trajectory:
                        self.trajectory = new_trajectory + self.trajectory
                        self.rightmost_position_pointer += TILE_LENGTH
                else:
                    # No next tile, which means we are headed out of playing field.
                    # Padding with a straight trajectory for now.
                    last_point = self.trajectory[0]
                    self.trajectory = [last_point + Vector2(-TILE_LENGTH + i, 0) for i in
                                       range(TILE_LENGTH)] + self.trajectory
                    self.rightmost_position_pointer += TILE_LENGTH

            if (self.rightmost_position_pointer + self.trajectory_pointer_increment) < (
                    len(self.trajectory) - TILE_LENGTH):
                # We can delete trajectory information from last tile
                self.trajectory = self.trajectory[:-TILE_LENGTH]

    @property
    def leftmost_position_pointer(self):
        return self.rightmost_position_pointer - self.length + 1

    @leftmost_position_pointer.setter
    def leftmost_position_pointer(self, p):
        self.rightmost_position_pointer = p + self.length - 1

    @property
    def trajectory_pointer_increment(self):
        if self.moving:
            if self.direction == FORWARD:
                return self.speed
            elif self.direction == BACKWARD:
                return -1*self.speed
        else:
            return 0

    @property
    def length(self):
        length = 0
        for wagon in self._wagons:
            length += wagon.length
        return length

    @property
    def rect(self):
        if self._wagons:
            rect = self._wagons.sprites()[0].rect
            return rect.unionall([wagon.rect for wagon in self._wagons.sprites()])
        else:
            return None

    @property
    def spawned(self) -> bool:
        return self._spawned

    @property
    def moving(self) -> bool:
        return self._moving

    @property
    def waiting(self) -> bool:
        return self._waiting

    @property
    def wagons(self) -> pg.sprite.Group:
        return self._wagons

    @property
    def entry_portal(self) -> str:
        return self._entry_portal

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def platform_status(self) -> str:
        return self._platform_status

    @property
    def exit_portal(self) -> str:
        return self._exit_portal

    @property
    def exit_portal_status(self) -> str:
        return self._exit_portal_status


