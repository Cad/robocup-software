/*
 * @file passOptimization.cpp
 * @author Alex Cunningham
 */

#include "passOptimization.hpp"

// implementations
#include <gtsam/NonlinearConstraint-inl.h>
#include <gtsam/NonlinearFactorGraph-inl.h>
#include <gtsam/TupleConfig-inl.h>
#include <gtsam/NonlinearOptimizer-inl.h>

using namespace Gameplay::Optimization;

// instantiations
namespace gtsam {
INSTANTIATE_NONLINEAR_FACTOR_GRAPH(Gameplay::Optimization::Config)
INSTANTIATE_NONLINEAR_CONSTRAINT(Gameplay::Optimization::Config)
INSTANTIATE_TUPLE_CONFIG3(Gameplay::Optimization::OppConfig, Gameplay::Optimization::SelfConfig, Gameplay::Optimization::BallConfig)
INSTANTIATE_NONLINEAR_OPTIMIZER(Gameplay::Optimization::Graph, Gameplay::Optimization::Config)
}

using namespace gtsam;
using namespace std;
using namespace Geometry2d;

Point2 Gameplay::Optimization::rc2gt_Point2(const Point& pt) {
	return Point2(pt.x, pt.y);
}

Point Gameplay::Optimization::gt2rc_Point2(const Point2& pt) {
	return Point(pt.x(), pt.y());
}

size_t Gameplay::Optimization::encodeID(uint8_t robotNum, size_t frame_num) {
	return frame_num + maxFrames*robotNum;
}

uint8_t Gameplay::Optimization::decodeRobot(size_t id) {
	return id/maxFrames;
}

size_t Gameplay::Optimization::decodeFrame(size_t id) {
	return id % maxFrames;
}
