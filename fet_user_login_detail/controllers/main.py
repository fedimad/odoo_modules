from odoo.addons.web.controllers.home import Home
from odoo.http import request, route
from datetime import datetime
from user_agents import parse
import os

# ---------------------------------------------------------
# Helper: find real filesystem session
# ---------------------------------------------------------

def find_real_session_file(uid):
    session_dir = '/opt/odoo17/.local/share/Odoo/sessions'

    if not os.path.exists(session_dir):
        return None

    for subdir in os.listdir(session_dir):
        subdir_path = os.path.join(session_dir, subdir)

        if not os.path.isdir(subdir_path):
            continue

        for filename in os.listdir(subdir_path):
            filepath = os.path.join(subdir_path, filename)

            try:
                with open(filepath, 'r', errors='ignore') as f:
                    if f'"uid": {uid}' in f.read():
                        return filename
            except:
                continue

    return None


# ---------------------------------------------------------
# LOGIN TRACKER
# ---------------------------------------------------------

class LoginTracker(Home):

    def web_login(self, redirect=None, **kw):
        response = super().web_login(redirect=redirect, **kw)

        if request.session.uid:
            # mark real login
            request.session['just_logged_in'] = True

            request.session['login_meta'] = {
                'ip': request.httprequest.remote_addr,
                'user_agent': request.httprequest.headers.get('User-Agent'),
            }

        return response


# ---------------------------------------------------------
# SESSION FINALIZER (REAL SESSION)
# ---------------------------------------------------------

class SessionTracker(Home):

    @route('/web', type='http', auth="user")
    def web_client(self, s_action=None, **kw):
        response = super().web_client(s_action=s_action, **kw)

        if request.session.get('just_logged_in'):

            user = request.env.user
            raw_sid = request.session.sid

            meta = request.session.get('login_meta', {})
            ip = meta.get('ip', 'N/A')
            ua_str = meta.get('user_agent', 'N/A')

            device = os_info = browser = 'Unknown'

            try:
                ua = parse(ua_str)

                if ua.is_mobile:
                    device = 'Mobile'
                elif ua.is_tablet:
                    device = 'Tablet'
                elif ua.is_pc:
                    device = 'Desktop'

                os_info = f"{ua.os.family} {ua.os.version_string}"
                browser = f"{ua.browser.family} {ua.browser.version_string}"

            except:
                pass

            # 🔥 get real session file
            session_file = find_real_session_file(user.id)

            request.env['login.detail'].sudo().create({
                'user_id': user.id,
                'login': user.login,
                'ip_address': ip,
                'user_agent': ua_str,
                # 'raw_session_id': raw_sid,
                'session_id': raw_sid or 'N/A',
                'device': device,
                'os': os_info,
                'browser': browser,
                'status': 'success',
                'login_date': datetime.now(),
                'is_session_active': True,
            })

            request.session['just_logged_in'] = False

        return response



