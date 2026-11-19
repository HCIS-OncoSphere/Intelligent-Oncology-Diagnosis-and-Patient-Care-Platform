from accounts.testing import BaseCase


class ImagingTests(BaseCase):
    def body(self, uid="1.2.840.1"):
        return dict(patient=self.pt1.id, orthanc_study_uid=uid, modality="CT", body_part="Abdomen",
                    study_date="2026-11-10",
                    series_in=[dict(orthanc_series_uid=uid + ".1", modality="CT", num_instances=120)])

    def test_staff_registers_study_patient_reads_own(self):
        self.as_doctor()
        r = self.c.post("/api/imaging/studies/", self.body(), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["series"][0]["num_instances"], 120)
        self.as_p1()
        self.assertEqual(len(self.c.get("/api/imaging/studies/").data), 1)
        self.assertEqual(self.c.post("/api/imaging/studies/", self.body("9.9"), format="json").status_code, 403)
        self.as_p2()
        self.assertEqual(len(self.c.get("/api/imaging/studies/").data), 0)

    def test_duplicate_uid_rejected(self):
        self.as_doctor()
        self.c.post("/api/imaging/studies/", self.body(), format="json")
        self.assertEqual(self.c.post("/api/imaging/studies/", self.body(), format="json").status_code, 400)

    def test_viewer_config(self):
        self.as_doctor()
        sid = self.c.post("/api/imaging/studies/", self.body(), format="json").data["id"]
        self.as_p1()
        cfg = self.c.get(f"/api/imaging/studies/{sid}/viewer-config/").data
        self.assertTrue(cfg["read_only"])
        self.assertTrue(cfg["dicomweb_root"].endswith("/dicom-web"))

    def test_patch_study_with_series_in_does_not_crash(self):
        self.as_doctor()
        sid = self.c.post("/api/imaging/studies/", self.body(), format="json").data["id"]
        r = self.c.patch(f"/api/imaging/studies/{sid}/", dict(body_part="Chest", series_in=[]), format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["body_part"], "Chest")
