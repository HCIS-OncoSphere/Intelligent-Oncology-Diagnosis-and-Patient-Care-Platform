"""Appointments tests: one test per validation rule plus role scoping.

Rule                                   Test
end after start                        test_end_before_start_rejected
not in the past                        test_past_booking_rejected
inside doctor availability             test_outside_availability_rejected
no double booking                      test_book_and_double_booking_rejected
patient not in two places at once      test_patient_cannot_be_in_two_places_at_once
doctors set only their own hours       test_doctor_changes_only_own_hours
status changes follow the flow         test_future_visit_cannot_be_marked_completed,
                                       test_cancelled_cannot_be_revived_into_a_taken_slot
cancel frees the slot                  test_cancel_frees_slot
patients see only their own            test_patient_cannot_see_others_appointments
"""
from datetime import time, timedelta

from django.utils import timezone

from accounts.models import User
from accounts.testing import AccountsTestBase
from appointments.models import Appointment, Doctor, DoctorAvailability

DR_PW, PT_PW, ADMIN_PW = "DoctorPassword123!", "PatientPassword123!", "AdminPassword123!"


def next_weekday_at(hour, minute=0):
    d = timezone.localtime() + timedelta(days=1)
    while d.weekday() > 4:
        d += timedelta(days=1)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)


class AppointmentBase(AccountsTestBase):
    def setUp(self):
        super().setUp()
        self.doctor = Doctor.objects.create(user=self.clinical_user, specialty="Oncology", license_no="L1")
        for d in range(5):  # Monday-Friday 09:00-17:00
            DoctorAvailability.objects.create(doctor=self.doctor, day_of_week=d, start_time=time(9), end_time=time(17))

    def as_doctor(self): self.login_user("dr_salma_test", DR_PW)
    def as_admin(self): self.login_user("admin_test", ADMIN_PW)
    def as_p1(self): self.login_user("patient_test", PT_PW)
    def as_p2(self): self.login_user("patient_test_2", PT_PW)

    def book(self, start, minutes=30, **extra):
        body = dict(doctor=self.doctor.id, start_time=start.isoformat(),
                    end_time=(start + timedelta(minutes=minutes)).isoformat(), reason="check")
        body.update(extra)
        return self.client.post("/api/appointments/", body, format="json")


class AppointmentRuleTests(AppointmentBase):
    def test_book_and_double_booking_rejected(self):
        self.as_p1()
        r = self.book(next_weekday_at(10))
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["status"], "scheduled")
        self.assertEqual(r.data["patient"], self.patient_profile_1.id)
        self.as_p2()
        r = self.book(next_weekday_at(10, 15))  # partly overlapping
        self.assertEqual(r.status_code, 400)
        self.assertIn("already booked", str(r.data))

    def test_back_to_back_is_allowed(self):
        self.as_p1()
        self.assertEqual(self.book(next_weekday_at(10)).status_code, 201)
        self.assertEqual(self.book(next_weekday_at(10, 30)).status_code, 201)

    def test_end_before_start_rejected(self):
        self.as_p1()
        r = self.book(next_weekday_at(10), minutes=-30)
        self.assertEqual(r.status_code, 400)
        self.assertIn("after start_time", str(r.data))

    def test_past_booking_rejected(self):
        self.as_p1()
        r = self.book(timezone.now() - timedelta(days=1))
        self.assertEqual(r.status_code, 400)
        self.assertIn("past", str(r.data))

    def test_outside_availability_rejected(self):
        self.as_p1()
        r = self.book(next_weekday_at(3))
        self.assertEqual(r.status_code, 400)
        self.assertIn("not available", str(r.data))
        r = self.book(next_weekday_at(16, 45))  # runs past 17:00
        self.assertEqual(r.status_code, 400)

    def test_doctor_without_availability_accepts_any_time(self):
        DoctorAvailability.objects.all().delete()
        self.as_p1()
        self.assertEqual(self.book(next_weekday_at(3)).status_code, 201)

    def test_cancel_frees_slot(self):
        self.as_p1()
        aid = self.book(next_weekday_at(12)).data["id"]
        r = self.client.post(f"/api/appointments/{aid}/cancel/")
        self.assertEqual(r.data["status"], "cancelled")
        self.assertEqual(self.client.post(f"/api/appointments/{aid}/cancel/").status_code, 400)  # only once
        self.assertEqual(self.book(next_weekday_at(12)).status_code, 201)


class AppointmentRoleTests(AppointmentBase):
    def test_patient_cannot_see_others_appointments(self):
        self.as_p1()
        aid = self.book(next_weekday_at(11)).data["id"]
        self.as_p2()
        self.assertEqual(len(self.client.get("/api/appointments/").data), 0)
        self.assertEqual(self.client.get(f"/api/appointments/{aid}/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/appointments/{aid}/cancel/").status_code, 404)
        self.as_doctor()
        self.assertEqual(len(self.client.get("/api/appointments/").data), 1)

    def test_patient_cannot_change_status_or_delete(self):
        self.as_p1()
        aid = self.book(next_weekday_at(11)).data["id"]
        r = self.client.patch(f"/api/appointments/{aid}/", dict(status="completed"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.client.delete(f"/api/appointments/{aid}/").status_code, 403)
        ok = self.client.patch(f"/api/appointments/{aid}/", dict(reason="Follow-up"), format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.data["reason"], "Follow-up")

    def test_patient_cannot_book_for_someone_else(self):
        self.as_p1()
        r = self.book(next_weekday_at(11), patient=self.patient_profile_2.id)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["patient"], self.patient_profile_1.id)

    def test_admin_booking_needs_patient(self):
        self.as_admin()
        self.assertEqual(self.book(next_weekday_at(14)).status_code, 400)
        r = self.book(next_weekday_at(14), patient=self.patient_profile_2.id)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["patient_mrn"], self.patient_profile_2.mrn)

    def test_doctor_cannot_book(self):
        self.as_doctor()
        r = self.book(next_weekday_at(14), patient=self.patient_profile_1.id)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Appointment.objects.count(), 0)
        # doctors still manage existing appointments
        self.as_p1()
        aid = self.book(next_weekday_at(15)).data["id"]
        self.as_doctor()
        self.assertEqual(self.client.post(f"/api/appointments/{aid}/cancel/").status_code, 200)

    def test_staff_marks_completed_and_no_show(self):
        past = timezone.now() - timedelta(hours=2)
        a = Appointment.objects.create(patient=self.patient_profile_1, doctor=self.doctor, booked_by=self.admin_user,
                                       start_time=past, end_time=past + timedelta(minutes=30))
        self.as_doctor()
        r = self.client.patch(f"/api/appointments/{a.id}/", dict(status="no_show"), format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], "no_show")
        # a finished visit is final
        r = self.client.patch(f"/api/appointments/{a.id}/", dict(status="completed"), format="json")
        self.assertEqual(r.status_code, 400)

    def test_future_visit_cannot_be_marked_completed(self):
        self.as_p1()
        aid = self.book(next_weekday_at(11)).data["id"]
        self.as_doctor()
        for status in ("completed", "no_show"):
            r = self.client.patch(f"/api/appointments/{aid}/", dict(status=status), format="json")
            self.assertEqual(r.status_code, 400)
            self.assertIn("only after it has started", str(r.data))

    def test_cancelled_cannot_be_revived_into_a_taken_slot(self):
        self.as_p1()
        aid = self.book(next_weekday_at(12)).data["id"]
        self.client.post(f"/api/appointments/{aid}/cancel/")
        self.as_p2()
        self.assertEqual(self.book(next_weekday_at(12)).status_code, 201)  # slot taken by someone else
        self.as_admin()
        r = self.client.patch(f"/api/appointments/{aid}/", dict(status="scheduled"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Appointment.objects.get(pk=aid).status, "cancelled")

    def test_patient_cannot_be_in_two_places_at_once(self):
        other = Doctor.objects.create(
            user=User.objects.create_user(username="dr_other", password="x", role=User.Role.CLINICAL),
            specialty="Radiology", license_no="L2")
        self.as_p1()
        start = next_weekday_at(10)
        self.assertEqual(self.book(start).status_code, 201)
        r = self.book(start + timedelta(minutes=15), doctor=other.id)
        self.assertEqual(r.status_code, 400)
        self.assertIn("another appointment", str(r.data))
        self.assertEqual(self.book(start + timedelta(minutes=30), doctor=other.id).status_code, 201)

    def test_bad_filters_are_400_not_500(self):
        self.as_admin()
        for q in ("doctor=abc", "patient=1x", "status=done", "date=2026-02-30", "date=tomorrow"):
            self.assertEqual(self.client.get(f"/api/appointments/?{q}").status_code, 400, q)
        self.assertEqual(self.client.get("/api/availability/?doctor=abc").status_code, 400)
        self.assertEqual(self.client.get(f"/api/appointments/?doctor={self.doctor.id}").status_code, 200)

    def test_unauthenticated_blocked(self):
        self.assertEqual(self.client.get("/api/appointments/").status_code, 401)
        self.assertEqual(self.client.get("/api/doctors/").status_code, 401)


class RescheduleAndSlotTests(AppointmentBase):
    def test_reschedule_uses_same_rules(self):
        self.as_p1()
        a = self.book(next_weekday_at(10)).data["id"]
        self.book(next_weekday_at(11))
        s = next_weekday_at(11)
        clash = self.client.post(f"/api/appointments/{a}/reschedule/",
                                 dict(start_time=s.isoformat(), end_time=(s + timedelta(minutes=30)).isoformat()),
                                 format="json")
        self.assertEqual(clash.status_code, 400)
        s = next_weekday_at(13)
        ok = self.client.post(f"/api/appointments/{a}/reschedule/",
                              dict(start_time=s.isoformat(), end_time=(s + timedelta(minutes=30)).isoformat()),
                              format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(Appointment.objects.get(pk=a).start_time, s)

    def test_cancelled_appointment_cannot_be_moved(self):
        self.as_p1()
        a = self.book(next_weekday_at(10)).data["id"]
        self.client.post(f"/api/appointments/{a}/cancel/")
        s = next_weekday_at(13)
        r = self.client.post(f"/api/appointments/{a}/reschedule/",
                             dict(start_time=s.isoformat(), end_time=(s + timedelta(minutes=30)).isoformat()),
                             format="json")
        self.assertEqual(r.status_code, 400)

    def test_free_slots_skip_booked_ones(self):
        self.as_p1()
        day = next_weekday_at(10)
        self.book(day)
        r = self.client.get(f"/api/doctors/{self.doctor.id}/slots/?date={day.date().isoformat()}")
        self.assertEqual(r.status_code, 200)
        starts = [timezone.localtime(timezone.datetime.fromisoformat(s["start_time"])).strftime("%H:%M")
                  for s in r.data["slots"]]
        self.assertEqual(len(starts), 15)  # 16 half-hours from 09:00 to 17:00, one is booked
        self.assertNotIn("10:00", starts)
        self.assertIn("09:30", starts)
        self.assertEqual(self.client.get(f"/api/doctors/{self.doctor.id}/slots/?date=bad").status_code, 400)

    def test_filters_and_reminders(self):
        self.as_doctor()
        tomorrow = timezone.localtime() + timedelta(days=1)
        Appointment.objects.create(patient=self.patient_profile_1, doctor=self.doctor, booked_by=self.clinical_user,
                                   start_time=tomorrow, end_time=tomorrow + timedelta(minutes=30))
        self.assertEqual(len(self.client.get(f"/api/appointments/?date={tomorrow.date().isoformat()}").data), 1)
        self.assertEqual(len(self.client.get("/api/appointments/?status=cancelled").data), 0)
        rem = self.client.get("/api/appointments/reminders/")
        self.assertEqual(rem.status_code, 200)
        self.assertEqual(rem.data[0]["patient_phone"], "01111222333")
        self.as_p1()
        self.assertEqual(self.client.get("/api/appointments/reminders/").status_code, 403)


class AvailabilityTests(AppointmentBase):
    def test_staff_manage_availability_patients_read(self):
        self.as_doctor()
        r = self.client.post("/api/availability/", dict(doctor=self.doctor.id, day_of_week=5,
                                                        start_time="10:00", end_time="14:00"), format="json")
        self.assertEqual(r.status_code, 201)
        overlap = self.client.post("/api/availability/", dict(doctor=self.doctor.id, day_of_week=5,
                                                              start_time="13:00", end_time="15:00"), format="json")
        self.assertEqual(overlap.status_code, 400)
        bad_day = self.client.post("/api/availability/", dict(doctor=self.doctor.id, day_of_week=9,
                                                              start_time="10:00", end_time="11:00"), format="json")
        self.assertEqual(bad_day.status_code, 400)
        self.as_p1()
        self.assertEqual(len(self.client.get(f"/api/availability/?doctor={self.doctor.id}").data), 6)
        self.assertEqual(self.client.post("/api/availability/", dict(doctor=self.doctor.id, day_of_week=6,
                                                                     start_time="10:00", end_time="11:00"),
                                          format="json").status_code, 403)

    def test_doctor_changes_only_own_hours(self):
        other = Doctor.objects.create(
            user=User.objects.create_user(username="dr_other", password="x", role=User.Role.CLINICAL),
            specialty="Radiology", license_no="L2")
        theirs = DoctorAvailability.objects.create(doctor=other, day_of_week=0, start_time=time(9), end_time=time(12))
        window = dict(doctor=other.id, day_of_week=2, start_time="13:00", end_time="15:00")
        self.as_doctor()
        self.assertEqual(self.client.post("/api/availability/", window, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/availability/{theirs.id}/").status_code, 404)
        self.assertEqual(self.client.patch(f"/api/availability/{theirs.id}/", dict(end_time="13:00"),
                                           format="json").status_code, 404)
        mine = DoctorAvailability.objects.get(doctor=self.doctor, day_of_week=4)  # no clash with theirs
        moved = self.client.patch(f"/api/availability/{mine.id}/", dict(doctor=other.id), format="json")
        self.assertEqual(moved.status_code, 403)  # cannot hand a window to someone else either
        self.assertEqual(len(self.client.get(f"/api/availability/?doctor={other.id}").data), 1)  # reading is fine
        self.as_admin()
        self.assertEqual(self.client.post("/api/availability/", window, format="json").status_code, 201)
        self.assertEqual(self.client.delete(f"/api/availability/{theirs.id}/").status_code, 204)

    def test_doctor_list_marks_own_profile(self):
        self.as_doctor()
        self.assertTrue(self.client.get("/api/doctors/").data[0]["is_me"])
        self.as_p1()
        self.assertFalse(self.client.get("/api/doctors/").data[0]["is_me"])

    def test_doctor_list_includes_availability(self):
        self.as_p1()
        d = self.client.get("/api/doctors/").data[0]
        self.assertEqual(d["name"], "Salma Oncologist")
        self.assertEqual(len(d["availability"]), 5)
