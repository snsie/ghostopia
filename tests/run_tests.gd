## Headless test runner. Finds every res://tests/**/test_*.gd file and runs
## each `test_*` method on a fresh instance. Exits 0 when everything passes,
## 1 otherwise. Prefer tools/run-tests.sh, which imports the project first.
##
##   godot --headless --path . -s res://tests/run_tests.gd
##   godot --headless --path . -s res://tests/run_tests.gd -- block_registry
##
## An optional user arg (after `--`) filters test files by substring.
extends SceneTree

const TEST_ROOT := "res://tests"


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var filter: String = args[0] if args.size() > 0 else ""

	var files: Array[String] = []
	_collect(TEST_ROOT, files)
	files.sort()

	var passed := 0
	var failed := 0
	var failed_names: Array[String] = []

	for path in files:
		if not filter.is_empty() and not path.contains(filter):
			continue
		var script := load(path) as GDScript
		if script == null or not script.can_instantiate():
			print("ERROR  %s: could not load (parse error?)" % path)
			failed += 1
			failed_names.append(path)
			continue

		var seen := {}
		for method in script.get_script_method_list():
			var test_name: String = method["name"]
			if not test_name.begins_with("test_") or seen.has(test_name):
				continue
			seen[test_name] = true

			var instance: Object = script.new()
			instance.tree = self
			instance.before_each()
			await instance.call(test_name)
			instance.after_each()
			instance._cleanup()

			var failures: Array[String] = instance._failures
			var label := "%s::%s" % [path.trim_prefix(TEST_ROOT + "/"), test_name]
			if failures.is_empty():
				passed += 1
				print("PASS   %s" % label)
			else:
				failed += 1
				failed_names.append(label)
				print("FAIL   %s" % label)
				for failure in failures:
					print("         %s" % failure)

	print("")
	print("%d passed, %d failed" % [passed, failed])
	if failed > 0:
		for test_name in failed_names:
			print("  failed: %s" % test_name)
	if passed + failed == 0:
		print("No tests matched.")
	quit(1 if failed > 0 else 0)


func _collect(dir_path: String, out: Array[String]) -> void:
	var dir := DirAccess.open(dir_path)
	if dir == null:
		return
	for sub in dir.get_directories():
		_collect(dir_path.path_join(sub), out)
	for file in dir.get_files():
		if file.begins_with("test_") and file.ends_with(".gd"):
			out.append(dir_path.path_join(file))
