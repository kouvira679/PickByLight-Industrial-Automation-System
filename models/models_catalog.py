MODELS = {
    1: {
        "model_name": "Red Product",
        "workplan": [
            {"task_code": 401, "part_name": "red top", "quantity": 1},
            {"task_code": 404, "part_name": "red bottom", "quantity": 1},
            {"task_code": 411, "part_name": "pcb", "quantity": 1},
            {"task_code": 412, "part_name": "fuse", "quantity": 2},
        ],
    },

    2: {
        "model_name": "Blue Product",
        "workplan": [
            {"task_code": 403, "part_name": "blue top", "quantity": 1},
            {"task_code": 405, "part_name": "blue bottom", "quantity": 1},
            {"task_code": 411, "part_name": "pcb", "quantity": 1},
            {"task_code": 412, "part_name": "fuse", "quantity": 2},
        ],
    },

    3: {
        "model_name": "Grey Product",
        "workplan": [
            {"task_code": 402, "part_name": "grey top", "quantity": 1},
            {"task_code": 406, "part_name": "grey bottom", "quantity": 1},
            {"task_code": 411, "part_name": "pcb", "quantity": 1},
            {"task_code": 412, "part_name": "fuse", "quantity": 2},
        ],
    },
}


def get_model(model_id):
    return MODELS.get(model_id)


def get_step_for_model(model_id, step_index):
    model = get_model(model_id)

    if model is None:
        raise ValueError(f"Unknown model_id: {model_id}")

    workplan = model["workplan"]

    if step_index < 0 or step_index >= len(workplan):
        raise IndexError(
            f"Step index {step_index} out of range for model {model_id}"
        )

    return workplan[step_index]