import numpy as np

from baseball_swing_analyzer.export_3d import generate_swing_3d_data_from_keypoints


def test_export_includes_bat_and_ball_estimates() -> None:
    seq = np.zeros((8, 17, 3), dtype=float)
    seq[:, :, 2] = 1.0
    seq[:, 9, :3] = [0.2, 0.2, 1.0]
    seq[:, 10, :3] = [0.4, 0.2, 1.0]
    seq[:, 7, :3] = [0.1, 0.3, 1.0]
    seq[:, 8, :3] = [0.5, 0.3, 1.0]
    phases = ["load", "load", "stride", "swing", "contact", "follow_through", "follow_through", "follow_through"]

    data = generate_swing_3d_data_from_keypoints(seq, phases, 30.0, {"contact_frame": 4})

    assert "bat" in data["frames"][4]
    assert len(data["frames"][4]["bat"]["handle"]) == 3
    assert len(data["frames"][4]["bat"]["barrel"]) == 3
    assert data["frames"][4]["bat"]["confidence"] > 0
    assert data["ball"]["contact_frame"] == 4
    assert len(data["ball"]["contact_position"]) == 3
