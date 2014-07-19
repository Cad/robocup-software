import robocup
import single_robot_composite_behavior
import behavior
import role_assignment
import constants
import evaluation.ball
import skills
import main
import enum
import math


class Goalie(single_robot_composite_behavior.SingleRobotCompositeBehavior):

    MaxX = constants.Field.GoalWidth / 2.0
    RobotSegment = robocup.Segment(robocup.Point(-MaxX, constants.Robot.Radius),
                                    robocup.Point(MaxX, constants.Robot.Radius))

    class State(enum.Enum):
        """Normal gameplay, stay towards the side of the goal that the ball is on."""
        defend = 1
        """Opponent has a ball and is prepping a shot we should block."""
        block = 2
        """The ball is moving towards our goal and we should catch it."""
        intercept = 3
        """Get the ball out of our defense area."""
        clear = 4
        """Prepare to block the opponent's penalty shot"""
        setup_penalty = 5
        """Keep calm and wait for the ball to be valid."""
        chill = 6

    def __init__(self):
        super().__init__(continuous=True)

        for substate in Goalie.State:
            self.add_state(substate, behavior.Behavior.State.running)

        self.add_transition(behavior.Behavior.State.start,
            Goalie.State.chill,
            lambda: True,
            "immediately")

        self.add_transition(Goalie.State.chill,
            Goalie.State.defend,
            lambda: main.ball().valid,
            "ball is valid")

        non_chill_states = [s for s in Goalie.State if s != Goalie.State.chill]

        # if ball is invalid, chill
        for state in non_chill_states:
            self.add_transition(state,
                Goalie.State.chill,
                lambda: not main.ball().valid,
                "ball is invalid")

        for state in non_chill_states:
            self.add_transition(state,
                Goalie.State.setup_penalty,
                lambda: main.game_state().is_their_penalty() and main.game_state().is_setup(),
                "setting up for opponent penalty")

        for state in [s2 for s2 in non_chill_states if s2 != Goalie.State.intercept]:
            self.add_transition(state,
                Goalie.State.intercept,
                lambda: evaluation.ball.is_moving_towards_our_goal() and evaluation.ball.opponent_with_ball() == None,
                "ball coming towards our goal")

        for state in [s2 for s2 in non_chill_states if s2 != Goalie.State.clear]:
            self.add_transition(state,
                Goalie.State.clear,
                lambda: evaluation.ball.is_in_our_goalie_zone() and
                        not evaluation.ball.is_moving_towards_our_goal(),
                "ball in our goalie box, but not headed toward goal")

        for state in [s2 for s2 in non_chill_states if s2 != Goalie.State.defend]:
            self.add_transition(state,
                Goalie.State.defend,
                lambda: not evaluation.ball.is_in_our_goalie_zone() and
                        not evaluation.ball.is_moving_towards_our_goal() and
                        evaluation.ball.opponent_with_ball() == None,
                'not much going on')

        for state in [s2 for s2 in non_chill_states if s2 != Goalie.State.block]:
            self.add_transition(state,
                Goalie.State.block,
                lambda: not evaluation.ball.is_in_our_goalie_zone() and
                        not evaluation.ball.is_moving_towards_our_goal() and
                        evaluation.ball.opponent_with_ball() != None,
                "opponents have possession")



    # note that execute_running() gets called BEFORE any of the execute_SUBSTATE methods gets called
    def execute_running(self):
        if self.robot != None:
            self.robot.face(main.ball().pos)


    def execute_chill(self):
        if self.robot != None:
            self.robot.move_to(robocup.Point(0, constants.Robot.Radius))


    def execute_setup_penalty(self):
        pt = Point(0, Field_PenaltyDist)
        penalty_kicker = min(main.opponent_robots(), key=lambda r: (r.pos - pt).mag())
        angle_rad = penalty_kicker.angle * constants.DegreesToRadians
        shot_line = Line(penalty_kicker.pos, penalty_kicker.pos + robocup.Point.direction(angle_rad))

        dest = shot_line.intersection(Goalie.RobotSegment)
        if dest == None:
            self.robot.move_to(robocup.Point(0, constants.Robot.Radius))
        else:
            dest.x = max(-Goalie.MaxX + constants.Robot.Radius, dest.x)
            dest.y = min(Goalie.MaxX - constants.Robot.Radius, dest.x)
        self.robot.move_to(dest)


    # The below is the old C++ code ported to python - instead of using this I've (justin) replaced it with the pivot kick behavior
    # remove this old stuff once we verify that the new behavior works well
    # def execute_clear(self):
    #     ball_to_goal = robocup.Segment(main.ball().pos, Point(0, 0))
    #     closest = ball_to_goal.nearest_point(robot.pos)

    #     if (robot.pos - closest).mag() > 0.10:
    #         robot.move_to(closest)
    #     else:
    #         robot.set_world_vel(main.ball().pos - robot.pos).normalized() * 1.0

    #     robot.dribble(40)
    #     robot.face(main.ball().pos())
    #     robot.unkick()

    #     if robot.has_chipper():
    #         robot.chip(255)
    #     else:
    #         robot.kick(255)

    def on_enter_clear(self):
        # FIXME: what we really want is a less-precise LineKick
        #           this will require a Capture behavior that doesn't wait for the ball to stop
        kick = skills.pivot_kick.PivotKick()

        # TODO: the below dribble speed is best for a 2011 bot
        # kick.dribble_speed = constants.Robot.Dribbler.MaxPower / 3.5

        # we use low error thresholds here
        # the goalie isn't trying to make a shot, he just wants get the ball the **** out of there
        kick.aim_params['error_threshold'] = 1.0
        kick.aim_params['max_steady_ang_vel'] = 12

        # chip
        kick.chip_power = constants.Robot.Chipper.MaxPower
        kick.use_chipper = True

        # FIXME: if the goalie has a fault, resort to bump

        self.add_subbehavior(kick, 'kick-clear', required=True)


    def on_exit_clear(self):
        self.remove_subbehavior('kick-clear')


    def execute_intercept(self):
        ball_path = robocup.Segment(main.ball().pos,
                            main.ball().pos + main.ball().vel.normalized()*10.0)
        dest = ball_path.nearest_point(self.robot.pos)
        self.robot.move_to(dest)

    def execute_block(self):
        opposing_kicker = evaluation.ball.opponent_with_ball()
        if opposing_kicker is not None:
            shot_line = robocup.Line(opposing_kicker.pos, main.ball().pos)
            block_circle = robocup.Circle(robocup.Point(0, 0), constants.Field.GoalWidth / 2.0)

            intersection_points = block_circle.intersects_line(shot_line)
            if len(intersection_points) > 0:
                dest = intersection_points[0]
                self.robot.move_to(dest)
            else:
                block_line = robocup.Line(robocup.Point(-Goalie.MaxX, constants.Robot.Radius),
                                    robocup.Point(Goalie.MaxX, constants.Robot.Radius))
                dest = block_line.line_intersection(shot_line)
                dest.x = min(Goalie.MaxX, dest.x)
                dest.x = max(-Goalie.MaxX, dest.x)
                self.robot.move_to(dest)
        else:
            self.robot.move_to(robocup.Point(0,constants.Robot.Radius))


    def execute_defend(self):
        dest_x = main.ball().pos.x / constants.Field.Width * Goalie.MaxX
        self.robot.move_to(robocup.Point(dest_x, constants.Robot.Radius))


    def role_requirements(self):
        reqs = super().role_requirements()

        for req in role_assignment.iterate_role_requirements_tree_leaves(reqs):
            req.required_shell_id = self.shell_id

        return reqs


    @property
    def shell_id(self):
        return self._shell_id
    @shell_id.setter
    def shell_id(self, value):
        self._shell_id = value