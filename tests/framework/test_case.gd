## Base class for headless tests. Test scripts extend this by path
## (extends "res://tests/framework/test_case.gd") so they work without the
## global class cache, which may not exist in a fresh worktree.
##
## Every method whose name starts with `test_` runs on a fresh instance.
## Tests may `await` (e.g. `await tree.process_frame`).
extends RefCounted

## The running SceneTree, for tests that need nodes or frames.
var tree: SceneTree

var _failures: Array[String] = []
var _nodes_to_free: Array[Node] = []


func before_each() -> void:
	pass


func after_each() -> void:
	pass


## Adds a node to the tree root and frees it after the test.
func add_to_tree(node: Node) -> Node:
	tree.root.add_child(node)
	_nodes_to_free.append(node)
	return node


func assert_true(condition: bool, message: String = "") -> void:
	if not condition:
		_fail("expected true", message)


func assert_false(condition: bool, message: String = "") -> void:
	if condition:
		_fail("expected false", message)


func assert_eq(actual: Variant, expected: Variant, message: String = "") -> void:
	if typeof(actual) != typeof(expected) or actual != expected:
		_fail("expected %s, got %s" % [var_to_str(expected), var_to_str(actual)], message)


func assert_ne(actual: Variant, unexpected: Variant, message: String = "") -> void:
	if typeof(actual) == typeof(unexpected) and actual == unexpected:
		_fail("did not expect %s" % var_to_str(unexpected), message)


func assert_almost_eq(actual: float, expected: float, tolerance: float = 0.0001, message: String = "") -> void:
	if absf(actual - expected) > tolerance:
		_fail("expected %f ± %f, got %f" % [expected, tolerance, actual], message)


func assert_null(value: Variant, message: String = "") -> void:
	if value != null:
		_fail("expected null, got %s" % var_to_str(value), message)


func assert_not_null(value: Variant, message: String = "") -> void:
	if value == null:
		_fail("expected non-null", message)


func assert_has(container: Variant, item: Variant, message: String = "") -> void:
	if not container.has(item):
		_fail("expected container to contain %s" % var_to_str(item), message)


func fail(message: String) -> void:
	_fail("failed", message)


func _fail(detail: String, message: String) -> void:
	_failures.append(detail if message.is_empty() else "%s: %s" % [message, detail])


func _cleanup() -> void:
	for node in _nodes_to_free:
		if is_instance_valid(node):
			node.queue_free()
	_nodes_to_free.clear()
