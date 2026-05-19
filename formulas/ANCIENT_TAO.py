
class AncientTaoEngine:
    def govern_defect(self, defect_type):
        mapping = {
            "Tok": 0.32, "Clw": 0.28, "Agt": 0.35, "Pan": 0.30,
            "Prm": 0.25, "Soul": 0.42, "Run": 0.30, "Net": 0.22,
            "Err": 0.45, "Mem": 0.38, "Res": 0.26, "Log": 0.34,
        }
        return mapping.get(defect_type, 0.2)
