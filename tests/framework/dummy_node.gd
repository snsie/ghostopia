## Minimal node used by tests/test_framework.gd. Counts _process calls.
extends Node

var process_calls: int = 0


func _process(_delta: float) -> void:
	process_calls += 1
