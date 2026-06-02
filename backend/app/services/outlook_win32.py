# backend/app/services/outlook_win32.py
"""
win32com wrapper for local Outlook access.
All COM calls are synchronous and must be dispatched via asyncio.to_thread()
from async callers so they don't block the event loop.

Each public method calls pythoncom.CoInitialize()/CoUninitialize() because
asyncio.to_thread runs in a ThreadPoolExecutor — those threads don't have COM
initialized by default and will crash without it.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.models.communication import MeetingAttendee, RawCalendarItem, RawEmail

logger = logging.getLogger(__name__)


def _is_win32com_available() -> bool:
    try:
        import win32com.client  # noqa: F401
        import pywintypes       # noqa: F401
        return True
    except ImportError:
        return False


class OutlookWin32Service:
    """Reads emails and calendar items from the local Outlook installation."""

    def is_available(self) -> bool:
        if not _is_win32com_available():
            return False
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            try:
                outlook = win32com.client.Dispatch("Outlook.Application")
                _ = outlook.Session
                return True
            except Exception:
                return False
            finally:
                pythoncom.CoUninitialize()
        except Exception:
            return False

    def get_accounts(self) -> list[str]:
        """Return display names of all accounts configured in Outlook."""
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            ns = outlook.GetNamespace("MAPI")
            names: list[str] = []
            for i in range(1, ns.Accounts.Count + 1):
                try:
                    names.append(ns.Accounts.Item(i).DisplayName)
                except Exception:
                    pass
            return names
        finally:
            pythoncom.CoUninitialize()

    def get_folders(self, account_display_name: str) -> list[str]:
        """Return top-level folder names for a given account."""
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            ns = outlook.GetNamespace("MAPI")
            store = self._find_store(ns, account_display_name)
            if store is None:
                return []
            folders: list[str] = []
            root = store.GetRootFolder()
            for i in range(1, root.Folders.Count + 1):
                try:
                    folders.append(root.Folders.Item(i).Name)
                except Exception:
                    pass
            return folders
        finally:
            pythoncom.CoUninitialize()

    def get_emails(
        self,
        account_display_name: str,
        folder_name: str,
        since: datetime,
    ) -> list[RawEmail]:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            ns = outlook.GetNamespace("MAPI")
            store = self._find_store(ns, account_display_name)
            if store is None:
                logger.warning("Outlook account not found: %s", account_display_name)
                return []

            folder = self._find_folder(store.GetRootFolder(), folder_name)
            if folder is None:
                logger.warning("Folder not found: %s in %s", folder_name, account_display_name)
                return []

            since_str = since.strftime("%m/%d/%Y %H:%M %p")
            try:
                items = folder.Items
                items.Sort("[ReceivedTime]", True)
                items = items.Restrict(f"[ReceivedTime] >= '{since_str}'")
            except Exception as e:
                logger.warning("Failed to filter Outlook items: %s", e)
                return []

            emails: list[RawEmail] = []
            count = 0
            try:
                item = items.GetFirst()
                while item is not None and count < 500:
                    try:
                        if item.Class == 43:  # olMail
                            emails.append(self._mail_to_raw(item, account_display_name, folder_name))
                            count += 1
                    except Exception:
                        pass
                    try:
                        item = items.GetNext()
                    except Exception:
                        break
            except Exception as e:
                logger.warning("Error iterating Outlook items: %s", e)

            return emails
        finally:
            pythoncom.CoUninitialize()

    def get_calendar_items(
        self,
        account_display_name: str,
        since: datetime,
        until: datetime,
    ) -> list[RawCalendarItem]:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            ns = outlook.GetNamespace("MAPI")
            store = self._find_store(ns, account_display_name)
            if store is None:
                return []

            cal_folder = self._find_folder(store.GetRootFolder(), "Calendar")
            if cal_folder is None:
                return []

            since_str = since.strftime("%m/%d/%Y %H:%M %p")
            until_str = until.strftime("%m/%d/%Y %H:%M %p")
            try:
                items = cal_folder.Items
                items.IncludeRecurrences = True
                items.Sort("[Start]")
                items = items.Restrict(
                    f"[Start] >= '{since_str}' AND [Start] <= '{until_str}'"
                )
            except Exception as e:
                logger.warning("Failed to filter calendar items: %s", e)
                return []

            cal_items: list[RawCalendarItem] = []
            count = 0
            try:
                item = items.GetFirst()
                while item is not None and count < 200:
                    try:
                        if item.Class == 26:  # olAppointment
                            cal_items.append(self._appt_to_raw(item))
                            count += 1
                    except Exception:
                        pass
                    try:
                        item = items.GetNext()
                    except Exception:
                        break
            except Exception as e:
                logger.warning("Error iterating calendar items: %s", e)

            return cal_items
        finally:
            pythoncom.CoUninitialize()

    def create_draft(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: Optional[list[str]] = None,
    ) -> str:
        """Create a draft in Outlook and return its EntryID."""
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)  # olMailItem
            mail.Subject = subject
            mail.Body = body
            mail.To = "; ".join(to)
            if cc:
                mail.CC = "; ".join(cc)
            mail.Save()
            return mail.EntryID
        finally:
            pythoncom.CoUninitialize()

    def respond_to_meeting(self, entry_id: str, response: str) -> None:
        """Accept, decline, or tentatively accept a meeting invite by its GlobalAppointmentID or EntryID.

        response: "accept" | "decline" | "tentative"
        Uses Respond() COM method to suppress any UI dialogs (fNoUI=True).
        olMeetingTentative=2, olMeetingAccepted=3, olMeetingDeclined=4
        """
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            ns = outlook.GetNamespace("MAPI")
            item = ns.GetItemFromID(entry_id)
            response_map = {"accept": 3, "tentative": 2, "decline": 4}
            code = response_map.get(response)
            if code is None:
                raise ValueError(f"Invalid response value: {response}")
            item.Respond(code, True)
            item.Save()
        finally:
            pythoncom.CoUninitialize()

    def update_draft(self, entry_id: str, body: str, subject: Optional[str] = None) -> None:
        """Update an existing Outlook draft by EntryID."""
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            ns = outlook.GetNamespace("MAPI")
            mail = ns.GetItemFromID(entry_id)
            mail.Body = body
            if subject:
                mail.Subject = subject
            mail.Save()
        finally:
            pythoncom.CoUninitialize()

    # -- Helpers -----------------------------------------------------------

    def _find_store(self, ns, account_display_name: str):
        for i in range(1, ns.Stores.Count + 1):
            try:
                store = ns.Stores.Item(i)
                if account_display_name.lower() in store.DisplayName.lower():
                    return store
            except Exception:
                pass
        return None

    def _find_folder(self, root_folder, folder_name: str):
        for i in range(1, root_folder.Folders.Count + 1):
            try:
                folder = root_folder.Folders.Item(i)
                if folder.Name.lower() == folder_name.lower():
                    return folder
            except Exception:
                pass
        return None

    def _resolve_smtp(self, address_entry) -> str:
        """Return SMTP address from an Outlook AddressEntry, falling back to .Address."""
        try:
            user = address_entry.GetExchangeUser()
            if user:
                return user.PrimarySmtpAddress or ""
        except Exception:
            pass
        try:
            return address_entry.Address or ""
        except Exception:
            return ""

    def _mail_to_raw(self, item, account: str, folder: str) -> RawEmail:
        try:
            received = item.ReceivedTime
            if hasattr(received, "isoformat"):
                received_dt = received.replace(tzinfo=timezone.utc)
            else:
                received_dt = datetime.now(timezone.utc)
        except Exception:
            received_dt = datetime.now(timezone.utc)

        # Resolve sender SMTP (internal Exchange accounts return a DN, not SMTP)
        sender = ""
        try:
            smtp = item.SenderEmailAddress or ""
            if "@" in smtp:
                sender = smtp
            else:
                sender = self._resolve_smtp(item.Sender) or getattr(item, "SenderName", "") or smtp
        except Exception:
            sender = getattr(item, "SenderName", "") or ""

        try:
            recipients = []
            for i in range(1, item.Recipients.Count + 1):
                r = item.Recipients.Item(i)
                addr = r.Address or ""
                if "@" not in addr:
                    addr = self._resolve_smtp(r.AddressEntry) or r.Name or addr
                if addr:
                    recipients.append(addr)
        except Exception:
            recipients = []

        try:
            attachments = [
                item.Attachments.Item(i).FileName
                for i in range(1, item.Attachments.Count + 1)
            ]
        except Exception:
            attachments = []

        return RawEmail(
            message_id=getattr(item, "EntryID", "") or "",
            subject=getattr(item, "Subject", "") or "",
            sender=sender,
            recipients=recipients,
            body=getattr(item, "Body", "") or "",
            received_at=received_dt,
            folder=folder,
            account=account,
            thread_id=getattr(item, "ConversationID", None),
            has_attachment=bool(attachments),
            attachment_names=attachments,
        )

    def _appt_to_raw(self, item) -> RawCalendarItem:
        try:
            start = item.Start
            start_dt = start.replace(tzinfo=timezone.utc) if hasattr(start, "isoformat") else datetime.now(timezone.utc)
        except Exception:
            start_dt = datetime.now(timezone.utc)

        try:
            end = item.End
            end_dt = end.replace(tzinfo=timezone.utc) if hasattr(end, "isoformat") else start_dt
        except Exception:
            end_dt = start_dt

        attendees: list[MeetingAttendee] = []
        try:
            for i in range(1, item.Recipients.Count + 1):
                r = item.Recipients.Item(i)
                addr = getattr(r, "Address", "") or ""
                if "@" not in addr:
                    addr = self._resolve_smtp(r.AddressEntry) or r.Name or addr
                status_map = {0: "none", 1: "none", 2: "tentative", 3: "accepted", 4: "declined", 5: "none"}
                attendees.append(MeetingAttendee(
                    name=getattr(r, "Name", "") or "",
                    email=addr,
                    response_status=status_map.get(getattr(r, "MeetingResponseStatus", 0), "none"),
                ))
        except Exception:
            pass

        body = getattr(item, "Body", "") or ""
        is_teams = "teams.microsoft.com" in body.lower()
        join_url: Optional[str] = None
        if is_teams:
            import re
            match = re.search(r"https://teams\.microsoft\.com/l/meetup-join/[^\s\"<]+", body)
            if match:
                join_url = match.group(0)

        response_map = {0: "none", 1: "none", 2: "tentative", 3: "accepted", 4: "declined"}
        my_response = response_map.get(getattr(item, "ResponseStatus", 0), "none")

        return RawCalendarItem(
            subject=getattr(item, "Subject", "") or "",
            organizer=getattr(item, "Organizer", "") or "",
            attendees=attendees,
            start_time=start_dt,
            end_time=end_dt,
            location=getattr(item, "Location", "") or "",
            body=body,
            is_teams_meeting=is_teams,
            teams_join_url=join_url,
            my_response=my_response,
            global_id=getattr(item, "GlobalAppointmentID", "") or "",
        )
