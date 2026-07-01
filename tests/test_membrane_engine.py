import unittest

from sizing_engines.membrane_engine_v2 import simulate_membrane_rated


class MembraneEngineTests(unittest.TestCase):
    def test_simulate_membrane_rated_accepts_selected_material_params(self):
        selected_params = {
            "name": "Polyimide Hollow-Fiber",
            "skin_thickness_microns": 0.1,
            "p_discharge_bar": 26.0,
            "permeate_pressure_bar": 1.2,
            "component_permeabilities_barrer": {
                "nitrogen": 0.25,
                "propylene": 15.0,
            },
        }

        rows, dew_notes = simulate_membrane_rated(
            650.0,
            1.2,
            337.15,
            0.95,
            0.05,
            selected_params=selected_params,
        )

        self.assertTrue(rows)
        self.assertTrue(dew_notes)


if __name__ == "__main__":
    unittest.main()
