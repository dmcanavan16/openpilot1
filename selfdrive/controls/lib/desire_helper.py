from cereal import log
from common.conversions import Conversions as CV
from common.params import Params
from common.realtime import DT_MDL
import numpy as np

LaneChangeState = log.LateralPlan.LaneChangeState
LaneChangeDirection = log.LateralPlan.LaneChangeDirection

LANE_CHANGE_SPEED_MIN = 20 * CV.MPH_TO_MS
LANE_CHANGE_TIME_MAX = 10.

DESIRES = {
  LaneChangeDirection.none: {
    LaneChangeState.off: log.LateralPlan.Desire.none,
    LaneChangeState.preLaneChange: log.LateralPlan.Desire.none,
    LaneChangeState.laneChangeStarting: log.LateralPlan.Desire.none,
    LaneChangeState.laneChangeFinishing: log.LateralPlan.Desire.none,
  },
  LaneChangeDirection.left: {
    LaneChangeState.off: log.LateralPlan.Desire.none,
    LaneChangeState.preLaneChange: log.LateralPlan.Desire.none,
    LaneChangeState.laneChangeStarting: log.LateralPlan.Desire.laneChangeLeft,
    LaneChangeState.laneChangeFinishing: log.LateralPlan.Desire.laneChangeLeft,
  },
  LaneChangeDirection.right: {
    LaneChangeState.off: log.LateralPlan.Desire.none,
    LaneChangeState.preLaneChange: log.LateralPlan.Desire.none,
    LaneChangeState.laneChangeStarting: log.LateralPlan.Desire.laneChangeRight,
    LaneChangeState.laneChangeFinishing: log.LateralPlan.Desire.laneChangeRight,
  },
}


class DesireHelper:
  def __init__(self):
    self.lane_change_state = LaneChangeState.off
    self.lane_change_direction = LaneChangeDirection.none
    self.lane_change_timer = 0.0
    self.lane_change_ll_prob = 1.0
    self.keep_pulse_timer = 0.0
    self.prev_one_blinker = False
    self.desire = log.LateralPlan.Desire.none

    # FrogPilot variables
    self.params = Params()
    self.nudgeless = self.params.get_bool("NudgelessLaneChange")
    self.lane_change_delay = self.params.get_int("LaneChangeTimer") if self.nudgeless else 0
    self.lane_detection = self.nudgeless and self.params.get_bool("LaneDetection")
    self.one_lane_change = self.nudgeless and self.params.get_bool("OneLaneChange")
    self.lane_available = False
    self.lane_change_completed = False
    self.lane_change_delay_checked = False
    self.lane_change_wait_timer = 0.0

  def update(self, carstate, lateral_active, lane_change_prob, md):
    v_ego = carstate.vEgo
    one_blinker = carstate.leftBlinker != carstate.rightBlinker
    below_lane_change_speed = v_ego < LANE_CHANGE_SPEED_MIN
    
    # Check the lane change delay just in case the user changed its mid drive
    if self.nudgeless and one_blinker and not self.lane_change_delay_checked:
      self.lane_change_delay = self.params.get_int("LaneChangeTimer")
      self.lane_change_delay_checked = True

    # Lane detection
    if self.lane_detection and one_blinker:
      # Set the minimum lane threshold to 2.6 meters
      min_lane_threshold = 2.6
      # Set the blinker index based on which signal is on
      blinker_index = 0 if carstate.leftBlinker else 1
      current_lane = md.laneLines[blinker_index + 1]
      desired_lane = md.laneLines[blinker_index] if carstate.leftBlinker else md.laneLines[blinker_index + 2]
      # Check if both the desired lane and the current lane have valid x and y values
      if all([desired_lane.x, desired_lane.y, current_lane.x, current_lane.y]) and len(desired_lane.x) == len(current_lane.x):
        # Interpolate the x and y values to the same length
        x = np.linspace(desired_lane.x[0], desired_lane.x[-1], num=len(desired_lane.x))
        lane_y = np.interp(x, current_lane.x, current_lane.y)
        desired_y = np.interp(x, desired_lane.x, desired_lane.y)
        # Calculate the width of the lane we're wanting to change into
        lane_width = np.abs(desired_y - lane_y)
        # Set lane_available to True if the lane width is larger than the threshold
        self.lane_available = np.amax(lane_width) >= min_lane_threshold
      else:
        self.lane_available = False
    else:
      # Default to setting "lane_available" to True
      self.lane_available = True

    if not lateral_active or self.lane_change_timer > LANE_CHANGE_TIME_MAX:
      self.lane_change_state = LaneChangeState.off
      self.lane_change_direction = LaneChangeDirection.none
    else:
      # LaneChangeState.off
      if self.lane_change_state == LaneChangeState.off and one_blinker and not self.prev_one_blinker and not below_lane_change_speed:
        self.lane_change_state = LaneChangeState.preLaneChange
        self.lane_change_ll_prob = 1.0
        self.lane_change_wait_timer = 0.0

      # LaneChangeState.preLaneChange
      elif self.lane_change_state == LaneChangeState.preLaneChange:
        # Set lane change direction
        self.lane_change_direction = LaneChangeDirection.left if \
          carstate.leftBlinker else LaneChangeDirection.right

        torque_applied = carstate.steeringPressed and \
                         ((carstate.steeringTorque > 0 and self.lane_change_direction == LaneChangeDirection.left) or
                          (carstate.steeringTorque < 0 and self.lane_change_direction == LaneChangeDirection.right))

        blindspot_detected = ((carstate.leftBlindspot and self.lane_change_direction == LaneChangeDirection.left) or
                              (carstate.rightBlindspot and self.lane_change_direction == LaneChangeDirection.right))

        # Conduct a nudgeless lane change if all the conditions are in place
        self.lane_change_wait_timer += DT_MDL
        if self.nudgeless and self.lane_available and not self.lane_change_completed and self.lane_change_wait_timer >= self.lane_change_delay:
          torque_applied = True
          self.lane_change_wait_timer = 0.0

        if not one_blinker or below_lane_change_speed:
          self.lane_change_state = LaneChangeState.off
          self.lane_change_direction = LaneChangeDirection.none
        elif torque_applied and not blindspot_detected:
          # Set the "lane_change_completed" flag to prevent any more lane changes if the toggle is on
          self.lane_change_completed = self.one_lane_change
          self.lane_change_state = LaneChangeState.laneChangeStarting

      # LaneChangeState.laneChangeStarting
      elif self.lane_change_state == LaneChangeState.laneChangeStarting:
        # fade out over .5s
        self.lane_change_ll_prob = max(self.lane_change_ll_prob - 2 * DT_MDL, 0.0)

        # 98% certainty
        if lane_change_prob < 0.02 and self.lane_change_ll_prob < 0.01:
          self.lane_change_state = LaneChangeState.laneChangeFinishing

      # LaneChangeState.laneChangeFinishing
      elif self.lane_change_state == LaneChangeState.laneChangeFinishing:
        # fade in laneline over 1s
        self.lane_change_ll_prob = min(self.lane_change_ll_prob + DT_MDL, 1.0)

        if self.lane_change_ll_prob > 0.99:
          self.lane_change_direction = LaneChangeDirection.none
          if one_blinker:
            self.lane_change_state = LaneChangeState.preLaneChange
          else:
            self.lane_change_state = LaneChangeState.off
            # Reset the "lane_change_completed" and "lane_change_delay_checked" flags
            self.lane_change_completed = False
            self.lane_change_delay_checked = False

    if self.lane_change_state in (LaneChangeState.off, LaneChangeState.preLaneChange):
      self.lane_change_timer = 0.0
    else:
      self.lane_change_timer += DT_MDL

    self.prev_one_blinker = one_blinker

    self.desire = DESIRES[self.lane_change_direction][self.lane_change_state]

    # Send keep pulse once per second during LaneChangeStart.preLaneChange
    if self.lane_change_state in (LaneChangeState.off, LaneChangeState.laneChangeStarting):
      self.keep_pulse_timer = 0.0
    elif self.lane_change_state == LaneChangeState.preLaneChange:
      self.keep_pulse_timer += DT_MDL
      if self.keep_pulse_timer > 1.0:
        self.keep_pulse_timer = 0.0
      elif self.desire in (log.LateralPlan.Desire.keepLeft, log.LateralPlan.Desire.keepRight):
        self.desire = log.LateralPlan.Desire.none
