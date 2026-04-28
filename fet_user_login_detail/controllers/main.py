# -*- coding: utf-8 -*-
from odoo.addons.web.controllers.home import Home
from odoo.http import request, route
from datetime import datetime
from user_agents import parse
import os
import hashlib
from odoo import http
from odoo.addons.web.controllers.session import Session
import logging

import logging

_logger = logging.getLogger(__name__)


def get_session_id_from_request():
    """Get the normalized session ID directly from the request"""
    if not request or not request.session:
        return None
    
    # Get the raw session ID
    raw_session_id = request.session.sid
    
    # Convert to SHA-1 hash (Odoo's filesystem format)
    normalized_session_id = hashlib.sha1(raw_session_id.encode('utf-8')).hexdigest()
    
    return normalized_session_id


def get_session_file_path(session_id):
    """Get the expected session file path without scanning"""
    if not session_id:
        return None
    
    session_dir = '/opt/odoo17/.local/share/Odoo/sessions'
    
    if len(session_id) >= 2:
        expected_path = os.path.join(session_dir, session_id[:2], session_id)
        if os.path.exists(expected_path):
            return expected_path
    
    return None


def find_real_session_file(uid):
    """Fallback: find session file by UID (only when direct method fails)"""
    session_dir = '/opt/odoo17/.local/share/Odoo/sessions'

    if not os.path.exists(session_dir):
        _logger.warning(f"Session directory not found: {session_dir}")
        return None

    try:
        for subdir in os.listdir(session_dir):
            subdir_path = os.path.join(session_dir, subdir)

            if not os.path.isdir(subdir_path):
                continue

            for filename in os.listdir(subdir_path):
                filepath = os.path.join(subdir_path, filename)

                try:
                    with open(filepath, 'r', errors='ignore') as f:
                        content = f.read(2000)  # Read only first 2000 chars for performance
                        if f'"uid": {uid}' in content:
                            _logger.info(f"Found session file for uid {uid}: {filename}")
                            return filename
                except Exception as e:
                    _logger.debug(f"Error reading {filepath}: {e}")
                    continue
    except Exception as e:
        _logger.error(f"Error scanning session directory: {e}")

    return None



class LoginTracker(Home):

    def web_login(self, redirect=None, **kw):
        response = super().web_login(redirect=redirect, **kw)

        if request.session.uid:

            ua_str = request.httprequest.headers.get('User-Agent', '')
            ip = request.httprequest.headers.get('X-Forwarded-For') or request.httprequest.remote_addr

            device = os_info = browser = 'Unknown'

            try:
                ua = parse(ua_str)

                if ua.is_mobile:
                    device = 'Mobile'
                elif ua.is_tablet:
                    device = 'Tablet'
                else:
                    device = 'Desktop'

                os_info = f"{ua.os.family} {ua.os.version_string}"
                browser = f"{ua.browser.family} {ua.browser.version_string}"

            except Exception:
                pass

            request.env['login.detail'].sudo().create({
                'user_id': request.session.uid,
                'login': request.env.user.login,
                'ip_address': ip,
                'user_agent': ua_str,
                'device': device,
                'os': os_info,
                'browser': browser,
                'session_id': request.session.sid,
                'status': 'success',
                'login_date': datetime.now(),
            })

        return response

    # STEP 2 → capture REAL session
    @route('/web', type='http', auth="user")
    def web_client(self, s_action=None, **kw):
        response = super().web_client(s_action=s_action, **kw)
        # Check if this is a fresh login
        if request.session:
            user = request.env.user
            meta = request.session.get('login_meta', {})

            ua_str = request.httprequest.headers.get('User-Agent', '')
            ip = request.httprequest.headers.get('X-Forwarded-For') or request.httprequest.remote_addr

            device = os_info = browser = 'Unknown'

            try:
                ua = parse(ua_str)

                if ua.is_mobile:
                    device = 'Mobile'
                elif ua.is_tablet:
                    device = 'Tablet'
                else:
                    device = 'Desktop'

                os_info = f"{ua.os.family} {ua.os.version_string}".strip()
                browser = f"{ua.browser.family} {ua.browser.version_string}".strip()
            except Exception as e:
                _logger.error(f"\n\nError parsing user agent: {e}\n\n")

            # Try direct method first (much faster and more reliable)
            session_id = get_session_id_from_request()
            session_file = get_session_file_path(session_id) if session_id else None
            # Fallback to scanning if direct method failed
            if not session_file:
                session_id = find_real_session_file(user.id)
            else:
                session_id = session_id  # Use the normalized ID

            # Check if we already have a record for this session to avoid duplicates
            existing_record = request.env['login.detail'].sudo().search([
                ('user_id', '=', user.id),
                ('session_id', '=', session_id ),
                ('status', '=', 'success'),
                ('create_date', '>=', datetime.now().replace(hour=0, minute=0, second=0))
            ], limit=1)
            if not existing_record:
                try:
                    request.env['login.detail'].sudo().create({
                        'user_id': user.id,
                        'login': user.login,
                        'ip_address': ip,
                        'user_agent': ua_str,
                        'session_id': request.session.sid or 'N/A',
                        # 'raw_session_id': request.session.sid if hasattr(request.session, 'sid') else 'N/A',
                        'device': device,
                        'os': os_info,
                        'browser': browser,
                        'status': 'success',
                        'login_date': datetime.now(),
                    })
                except Exception as e:
                    _logger.error(f"\n\nFailed to create login record: {e}\n\n")
            else:
                _logger.warning(f"\n\nDuplicate login attempt prevented for {user.login}\n\n")

            

            # VERY IMPORTANT → reset flag

        return response






######################################
############# logout #################
######################################
def normalize_session_id(raw_sid):
    if not raw_sid:
        return None
    return hashlib.sha1(raw_sid.encode('utf-8')).hexdigest()


class LogoutTracker(Session):

    @http.route('/web/session/logout', type='http', auth="user")
    def logout(self, redirect='/web/login', **kw):
        """Override logout to mark session as ended"""

        uid = request.session.uid
        raw_sid = request.session.sid

        session_id = normalize_session_id(raw_sid)

        _logger.info(f"\n🔴 LOGOUT detected for UID={uid}, SID={session_id}\n")

        if uid and session_id:
            try:
                # Find active session
                session_record = request.env['login.detail'].sudo().search([
                    ('user_id', '=', uid),
                    ('session_id', '=', session_id),
                    ('status', '=', 'success'),
                ], limit=1)

                if session_record:
                    session_record.write({
                        'status': 'logout',
                        'logout_date': datetime.now(),
                        'is_session_active': False,
                        # 'active': True,
                    })


                else:
                    _logger.warning(f"No session record found for logout UID={uid}")

            except Exception as e:
                _logger.error(f"Error updating logout session: {e}")

        # Call original logout (VERY IMPORTANT)
        return super().logout(redirect=redirect, **kw)

