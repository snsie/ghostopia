## Proves the runner works: assertions, the scene tree, and awaited frames.
extends "res://tests/framework/test_case.gd"


func test_assertions_pass() -> void:
	assert_true(true)
	assert_false(false)
	assert_eq(2 + 2, 4)
	assert_ne("a", "b")
	assert_almost_eq(0.1 + 0.2, 0.3)
	assert_has([1, 2, 3], 2)


func test_scene_tree_and_frames() -> void:
	var node: Node = add_to_tree(load("res://tests/framework/dummy_node.gd").new())
	assert_true(node.is_inside_tree())
	await tree.process_frame
	await tree.process_frame
	assert_true(node.process_calls >= 1, "node should have processed at least once")
