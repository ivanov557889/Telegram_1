#!/usr/bin/env python3
import os, sys, re as re_mod

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, "TMessagesProj", "src", "main", "java")

# API CREDENTIALS
API_ID = "2040"
API_HASH = "b18441a1ff607e10a989891a5462e627"

def find_file(name):
    for dp, _, files in os.walk(SRC):
        if name in files: return os.path.join(dp, name)
    return None

def read(p):
    with open(p, encoding="utf-8") as f: return f.read()

def write(p, t):
    with open(p, "w", encoding="utf-8") as f: f.write(t)
    print(f"✔ {os.path.relpath(p, ROOT)}")

def find_method_end(text, open_brace):
    depth = 0; i = open_brace
    while i < len(text):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0: return i
        i += 1
    return len(text) - 1

def insert_before(path, marker, insertion):
    text = read(path)
    if insertion.strip() in text: print(f"↩ skip {os.path.relpath(path,ROOT)}"); return True
    if marker not in text: print(f"✘ NOT FOUND: {marker!r}", file=sys.stderr); return False
    write(path, text.replace(marker, insertion + "\n" + marker, 1)); return True

def insert_after(path, marker, insertion):
    text = read(path)
    if insertion.strip() in text: print(f"↩ skip {os.path.relpath(path,ROOT)}"); return True
    if marker not in text: print(f"✘ NOT FOUND: {marker!r}", file=sys.stderr); return False
    write(path, text.replace(marker, marker + "\n" + insertion, 1)); return True

GIFTS_JAVA = '''\
package org.telegram.ui;

import org.json.JSONArray;
import org.json.JSONObject;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.MessagesController;
import org.telegram.tgnet.ConnectionsManager;
import org.telegram.tgnet.TLRPC;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.lang.reflect.Field;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashSet;

public class WeryGramGifts {

    private static final String GIFTS_URL =
        "https://raw.githubusercontent.com/binbash-0/DeletedGifts-Plugin/refs/heads/main/gift_list.json";
    private static volatile boolean injected = false;

    private static Object getF(Object o, String n) {
        if (o == null) return null;
        try { return o.getClass().getField(n).get(o); }
        catch (Exception e) {
            try { Field f = o.getClass().getDeclaredField(n); f.setAccessible(true); return f.get(o); }
            catch (Exception ex) { return null; }
        }
    }
    private static void setF(Object o, String n, Object v) {
        if (o == null) return;
        try { o.getClass().getField(n).set(o, v); }
        catch (Exception e) {
            try { Field f = o.getClass().getDeclaredField(n); f.setAccessible(true); f.set(o, v); }
            catch (Exception ex) {}
        }
    }

    public static void reset() { injected = false; }

    public static void injectDeletedGifts(int account) {
        if (!MessagesController.getGlobalMainSettings().getBoolean("wery_deleted_gifts", false)) return;
        new Thread(() -> {
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL(GIFTS_URL).openConnection();
                conn.setConnectTimeout(5000); conn.setReadTimeout(5000);
                BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder(); String line;
                while ((line = br.readLine()) != null) sb.append(line);
                br.close(); conn.disconnect();
                JSONArray arr = new JSONObject(sb.toString()).getJSONArray("gifts");
                final long[] ids = new long[arr.length()]; final int[] prices = new int[arr.length()];
                for (int i = 0; i < arr.length(); i++) {
                    JSONObject g = arr.getJSONObject(i);
                    ids[i] = g.getLong("id"); prices[i] = g.getInt("price");
                }
                AndroidUtilities.runOnUIThread(() -> doInject(account, ids, prices));
            } catch (Exception ignored) {}
        }).start();
    }

    @SuppressWarnings({"unchecked","rawtypes"})
    private static void doInject(int account, long[] ids, int[] prices) {
        if (injected) return;
        try {
            Class<?> sc = Class.forName("org.telegram.ui.Stars.StarsController");
            Object ctrl = sc.getMethod("getInstance", int.class).invoke(null, account);
            ArrayList gifts = null;
            for (String fn : new String[]{"gifts","starGifts","allGifts"}) {
                try {
                    Field f = sc.getDeclaredField(fn); f.setAccessible(true);
                    Object v = f.get(ctrl);
                    if (v instanceof ArrayList && !((ArrayList)v).isEmpty()) { gifts=(ArrayList)v; break; }
                } catch (Exception ignored) {}
            }
            if (gifts == null || gifts.isEmpty()) return;
            Object donor = gifts.get(0);
            HashSet<Long> existing = new HashSet<>();
            for (Object o : new ArrayList(gifts)) {
                Object cid = getF(o,"id");
                if (cid instanceof Long) existing.add((Long)cid);
                else if (cid instanceof Number) existing.add(((Number)cid).longValue());
            }
            int pos0 = Math.min(11, gifts.size()); int cnt = 0;
            for (int i = 0; i < ids.length; i++) {
                if (existing.contains(ids[i])) continue;
                try {
                    Object clone = donor.getClass().getDeclaredConstructor().newInstance();
                    for (String f2 : new String[]{"flags","sticker","convert_stars"}) {
                        Object v = getF(donor,f2); if (v != null) setF(clone,f2,v);
                    }
                    setF(clone,"id",ids[i]); setF(clone,"gift_id",ids[i]);
                    setF(clone,"stars",prices[i]); setF(clone,"sold_out",false);
                    setF(clone,"attributes",new ArrayList<>());
                    gifts.add(Math.min(pos0+cnt, gifts.size()), clone); cnt++;
                } catch (Exception ignored) {}
            }
            for (String sf : new String[]{"sortedGifts","birthdaySortedGifts"}) {
                try {
                    Field f = sc.getDeclaredField(sf); f.setAccessible(true);
                    ArrayList sorted = (ArrayList)f.get(ctrl);
                    if (sorted != null && sorted != gifts)
                        for (int i=0;i<cnt;i++) sorted.add(Math.min(pos0+i,sorted.size()), gifts.get(pos0+i));
                } catch (Exception ignored) {}
            }
            injected = true;
        } catch (Exception ignored) {}
    }

    public static void joinWeryGram(int account) {
        if (MessagesController.getGlobalMainSettings().getBoolean("wery_joined_ch", false)) return;
        MessagesController.getGlobalMainSettings().edit().putBoolean("wery_joined_ch", true).apply();
        AndroidUtilities.runOnUIThread(() -> {
            try {
                TLRPC.TL_contacts_resolveUsername req = new TLRPC.TL_contacts_resolveUsername();
                req.username = "werygram";
                ConnectionsManager.getInstance(account).sendRequest(req, (response, error) -> {
                    if (!(response instanceof TLRPC.TL_contacts_resolvedPeer)) return;
                    TLRPC.TL_contacts_resolvedPeer resolved = (TLRPC.TL_contacts_resolvedPeer) response;
                    if (resolved.chats == null || resolved.chats.isEmpty()) return;
                    TLRPC.Chat ch = resolved.chats.get(0);
                    try {
                        TLRPC.TL_channels_joinChannel join = new TLRPC.TL_channels_joinChannel();
                        TLRPC.TL_inputChannel ic = new TLRPC.TL_inputChannel();
                        ic.channel_id = ch.id; ic.access_hash = ch.access_hash;
                        join.channel = ic;
                        ConnectionsManager.getInstance(account).sendRequest(join, (r2, e2) -> {
                            try {
                                TLRPC.TL_messages_toggleDialogPin pin = new TLRPC.TL_messages_toggleDialogPin();
                                pin.pinned = true;
                                TLRPC.TL_inputDialogPeer dp = new TLRPC.TL_inputDialogPeer();
                                TLRPC.TL_inputPeerChannel ipc = new TLRPC.TL_inputPeerChannel();
                                ipc.channel_id = ch.id; ipc.access_hash = ch.access_hash;
                                dp.peer = ipc; pin.peer = dp;
                                ConnectionsManager.getInstance(account).sendRequest(pin, null);
                            } catch (Exception ignored) {}
                        });
                    } catch (Exception ignored) {}
                });
            } catch (Exception ignored) {}
        }, 4000);
    }
}
'''

ACTIVITY = '''\
package org.telegram.ui;

import android.content.Context;
import android.content.SharedPreferences;
import android.widget.LinearLayout;
import android.widget.Switch;
import android.widget.TextView;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.MessagesController;
import org.telegram.messenger.NotificationCenter;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;

public class WeryGramPremiumActivity extends BaseFragment {

    private SharedPreferences prefs;
    private int account;

    interface OnEnable { void run(); }

    private void addRow(Context ctx, LinearLayout parent,
                        String title, String sub, String key, OnEnable onEnable) {
        LinearLayout row = new LinearLayout(ctx);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(AndroidUtilities.dp(16), AndroidUtilities.dp(14),
                       AndroidUtilities.dp(16), AndroidUtilities.dp(14));
        row.setGravity(android.view.Gravity.CENTER_VERTICAL);
        LinearLayout labels = new LinearLayout(ctx);
        labels.setOrientation(LinearLayout.VERTICAL);
        labels.setLayoutParams(new LinearLayout.LayoutParams(
            0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        TextView t = new TextView(ctx);
        t.setText(title);
        t.setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP, 16);
        t.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText));
        TextView s = new TextView(ctx);
        s.setText(sub);
        s.setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP, 13);
        s.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2));
        labels.addView(t); labels.addView(s);
        android.view.View div = new android.view.View(ctx);
        div.setBackgroundColor(Theme.getColor(Theme.key_divider));
        LinearLayout.LayoutParams dp2 = new LinearLayout.LayoutParams(
            AndroidUtilities.dp(1), AndroidUtilities.dp(40));
        dp2.setMargins(AndroidUtilities.dp(12), 0, AndroidUtilities.dp(12), 0);
        div.setLayoutParams(dp2);
        Switch toggle = new Switch(ctx);
        toggle.setChecked(prefs.getBoolean(key, false));
        toggle.setOnCheckedChangeListener((btn, checked) -> {
            prefs.edit().putBoolean(key, checked).apply();
            NotificationCenter.getGlobalInstance()
                .postNotificationName(NotificationCenter.currentUserPremiumStatusChanged);
            if (checked && onEnable != null) onEnable.run();
        });
        row.addView(labels); row.addView(div); row.addView(toggle);
        parent.addView(row);
        android.view.View divider = new android.view.View(ctx);
        divider.setBackgroundColor(Theme.getColor(Theme.key_divider));
        divider.setLayoutParams(new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 1));
        parent.addView(divider);
    }

    @Override
    public android.view.View createView(Context context) {
        actionBar.setBackButtonImage(org.telegram.messenger.R.drawable.ic_ab_back);
        actionBar.setTitle("WeryGram");
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override public void onItemClick(int id) { if (id == -1) finishFragment(); }
        });
        prefs   = MessagesController.getGlobalMainSettings();
        account = currentAccount;
        WeryGramGifts.joinWeryGram(account);
        LinearLayout root = new LinearLayout(context);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
        addRow(context, root,
            "Visual Premium",
            "Дает визуально Telegram Premium",
            "wery_visual_premium", null);
        addRow(context, root,
            "Режим Призрака",
            "Вы будете в статусе невидимки, при по",
            "wery_ghost_mode", null);
        addRow(context, root,
            "Удалённые подарки",
            "Вы можете дарить удалённые подарки",
            "wery_deleted_gifts",
            () -> { WeryGramGifts.reset(); WeryGramGifts.injectDeletedGifts(account); });
        fragmentView = root;
        return fragmentView;
    }
}
'''

def patch_user_config(errors):
    uc = find_file("UserConfig.java")
    if not uc: print("✘ UserConfig.java not found", file=sys.stderr); return errors+1
    text = read(uc)
    if 'wery_visual_premium' in text: print("↩ skip UserConfig"); return errors
    sig_pos = text.find("getCurrentUser()")
    if sig_pos == -1: print("✘ getCurrentUser() не найден", file=sys.stderr); return errors+1
    ret_pos = text.find("return currentUser;", sig_pos)
    if ret_pos == -1: print("✘ return currentUser; не найден", file=sys.stderr); return errors+1
    line_start = text.rfind('\n', 0, ret_pos) + 1
    indent = ''
    for ch in text[line_start:ret_pos]:
        if ch in (' ','\t'): indent += ch
        else: break
    
    patch = (
        indent + 'try {\n' +
        indent + '    android.content.SharedPreferences __p = org.telegram.messenger.MessagesController.getGlobalMainSettings();\n' +
        indent + '    if (currentUser != null && __p.getBoolean("wery_visual_premium", false)) {\n' +
        indent + '        currentUser.premium = true;\n' +
        indent + '        if (currentUser.emoji_status instanceof org.telegram.tgnet.TLRPC.TL_emojiStatus) {\n' +
        indent + '            long __curEid=((org.telegram.tgnet.TLRPC.TL_emojiStatus)currentUser.emoji_status).document_id;\n' +
        indent + '            if(__curEid!=0){__p.edit().putLong("wery_emoji_id",__curEid).apply();}\n' +
        indent + '            else{long __se=__p.getLong("wery_emoji_id",0);if(__se!=0)((org.telegram.tgnet.TLRPC.TL_emojiStatus)currentUser.emoji_status).document_id=__se;}\n' +
        indent + '        }else{\n' +
        indent + '            long __se=__p.getLong("wery_emoji_id",0);\n' +
        indent + '            if(__se!=0){org.telegram.tgnet.TLRPC.TL_emojiStatus __es=new org.telegram.tgnet.TLRPC.TL_emojiStatus();__es.document_id=__se;currentUser.emoji_status=__es;}\n' +
        indent + '        }\n' +
        indent + '        if(currentUser.profile_color!=null){\n' +
        indent + '            int __cc=currentUser.profile_color.color;long __ce=currentUser.profile_color.background_emoji_id;\n' +
        indent + '            if(__cc>=0||__ce!=0){__p.edit().putInt("wery_pcolor_id",__cc).putLong("wery_pcolor_emoji",__ce).apply();}\n' +
        indent + '            else{int __sp=__p.getInt("wery_pcolor_id",-1);long __se=__p.getLong("wery_pcolor_emoji",0);if(__sp>=0)currentUser.profile_color.color=__sp;if(__se!=0)currentUser.profile_color.background_emoji_id=__se;}\n' +
        indent + '        }else{\n' +
        indent + '            int __sp=__p.getInt("wery_pcolor_id",-1);long __se=__p.getLong("wery_pcolor_emoji",0);\n' +
        indent + '            if(__sp>=0||__se!=0){currentUser.profile_color=new org.telegram.tgnet.TLRPC.TL_peerColor();if(__sp>=0)currentUser.profile_color.color=__sp;currentUser.profile_color.background_emoji_id=__se;}\n' +
        indent + '        }\n' +
        indent + '        if(currentUser.color!=null){\n' +
        indent + '            int __nc=currentUser.color.color;long __ne=currentUser.color.background_emoji_id;\n' +
        indent + '            if(__nc>=0||__ne!=0){__p.edit().putInt("wery_color_id",__nc).putLong("wery_color_emoji",__ne).apply();}\n' +
        indent + '            else{int __sc=__p.getInt("wery_color_id",-1);long __sce=__p.getLong("wery_color_emoji",0);if(__sc>=0)currentUser.color.color=__sc;if(__sce!=0)currentUser.color.background_emoji_id=__sce;}\n' +
        indent + '        }else{\n' +
        indent + '            int __sc=__p.getInt("wery_color_id",-1);long __sce=__p.getLong("wery_color_emoji",0);\n' +
        indent + '            if(__sc>=0||__sce!=0){currentUser.color=new org.telegram.tgnet.TLRPC.TL_peerColor();if(__sc>=0)currentUser.color.color=__sc;currentUser.color.background_emoji_id=__sce;}\n' +
        indent + '        }\n' +
        indent + '    }\n' +
        indent + '} catch (Exception __e) {}\n' +
        indent
    )
    write(uc, text[:ret_pos] + patch + text[ret_pos:])
    return errors


def patch_messages_controller(errors):
    mc = find_file("MessagesController.java")
    if not mc: print("✘ MessagesController.java not found", file=sys.stderr); return errors+1
    text = read(mc); modified = False

    if 'wery_visual_premium' not in text:
        variants = ["public TLRPC.User getUser(Long id) {",
                    "public TLRPC.User getUser(Long uid) {",
                    "public TLRPC.User getUser(Long javaLong) {"]
        marker = next((v for v in variants if v in text), None)
        if marker:
            var = "id" if "Long id)" in marker else ("uid" if "Long uid)" in marker else "javaLong")
            ins = (
                "        if(" + var + "!=null && " + var + ".longValue()==UserConfig.getInstance(currentAccount).getClientUserId()\n" +
                '            && org.telegram.messenger.MessagesController.getGlobalMainSettings().getBoolean("wery_visual_premium",false)){\n' +
                "            org.telegram.tgnet.TLRPC.User __u=users.get(" + var + ");\n" +
                "            if(__u!=null&&!__u.bot)__u.premium=true;\n" +
                "        }"
            )
            text = text.replace(marker, marker+"\n"+ins, 1); modified=True
            print("✔ MC: premium patch")

    if 'wery_verified_ch' not in text:
        chat_variants = ["public TLRPC.Chat getChat(Long id) {",
                         "public TLRPC.Chat getChat(Long chatId) {"]
        cm = next((v for v in chat_variants if v in text), None)
        if cm:
            cvar = "id" if "Long id)" in cm else "chatId"
            cins = (
                "        try{\n" +
                "            org.telegram.tgnet.TLRPC.Chat __ch=chats.get(" + cvar + ");\n" +
                '            if(__ch!=null&&"werygram".equals(__ch.username)){__ch.verified=true;}\n' +
                "        }catch(Exception __ce){}"
            )
            text = text.replace(cm, cm+"\n"+cins, 1); modified=True
            print("✔ MC: @werygram verification patch")

    if 'wery_ghost_online' not in text:
        for m in ["public void sendOnlineIfNeed() {", "void sendOnlineIfNeed() {"]:
            if m in text:
                text = text.replace(m,
                    m+'\n        if(org.telegram.messenger.MessagesController.getGlobalMainSettings().getBoolean("wery_ghost_mode",false))return;',1)
                modified=True; print("✔ Ghost: online patch"); break

    if 'wery_ghost_read' not in text:
        for m in ["public void markDialogAsRead(",
                  "public void readMessages(",
                  "public void markMessagesAsRead("]:
            if m in text:
                bp = text.find('{', text.find(m))
                if bp != -1:
                    text = text[:bp+1]+'\n        if(org.telegram.messenger.MessagesController.getGlobalMainSettings().getBoolean("wery_ghost_mode",false))return;'+text[bp+1:]
                    modified=True; print("✔ Ghost: read patch")
                break

    if modified: write(mc, text)
    return errors


def patch_stars_controller(errors):
    sc = find_file("StarsController.java")
    if not sc: print("⚠ StarsController.java не найден"); return errors
    text = read(sc)
    if 'wery_deleted_gifts' in text: print("↩ skip StarsController"); return errors
    m = next((x for x in ["giftsLoaded = true;","this.giftsLoaded = true;"] if x in text), None)
    if m:
        injection = m + '\n        if(org.telegram.messenger.MessagesController.getGlobalMainSettings().getBoolean("wery_deleted_gifts",false)){org.telegram.ui.WeryGramGifts.reset();org.telegram.ui.WeryGramGifts.injectDeletedGifts(account);}'
        write(sc, text.replace(m, injection))
        print("✔ StarsController: deleted gifts patch")
    else:
        print("⚠ StarsController: giftsLoaded marker не найден")
    return errors


def patch_app_name(errors):
    candidates = [
        os.path.join(ROOT, "TMessagesProj", "src", "main", "res", "values", "strings.xml"),
        os.path.join(ROOT, "TMessagesProj", "src", "main", "res", "values-en", "strings.xml"),
    ]
    for path in candidates:
        if not os.path.exists(path): continue
        text = read(path)
        if 'WeryGram' in text: print("↩ skip strings.xml"); return errors
        new_text = re_mod.sub(
            r'(<string name="AppName">)[^<]*(</string>)',
            r'\1WeryGram\2', text)
        if new_text != text:
            write(path, new_text)
            print("✔ AppName → WeryGram")
            return errors
    res_base = os.path.join(ROOT, "TMessagesProj", "src", "main", "res")
    for dp, _, files in os.walk(res_base):
        if 'strings.xml' not in files: continue
        path = os.path.join(dp, 'strings.xml')
        text = read(path)
        if 'WeryGram' in text or 'AppName' not in text: continue
        new_text = re_mod.sub(
            r'(<string name="AppName">)[^<]*(</string>)',
            r'\1WeryGram\2', text)
        if new_text != text:
            write(path, new_text)
            print("✔ AppName → WeryGram")
            return errors
    print("⚠ AppName не найден в strings.xml")
    return errors


def patch_drawer_layout(errors):
    """Заменяет название Telegram на WeryGram в главном меню"""
    files_to_check = [
        "LaunchActivity.java",
        "DrawerLayoutActivity.java",
        "MainActivity.java",
    ]
    
    for fname in files_to_check:
        layout_file = find_file(fname)
        if not layout_file: continue
        
        text = read(layout_file)
        if 'wery_drawer_title' in text:
            print(f"↩ skip {fname}"); 
            return errors
        
        if 'getString(R.string.AppName)' in text and 'wery' not in text:
            old = 'getString(R.string.AppName)'
            new = '(org.telegram.messenger.MessagesController.getGlobalMainSettings().getBoolean("wery_visual_premium",false) ? "WeryGram" : getString(R.string.AppName))'
            text = text.replace(old, new, 1)
            write(layout_file, text)
            print(f"✔ {fname}: app title patch")
            return errors
    
    print("⚠ Drawer layout file not found")
    return errors


def patch_api_credentials(errors):
    """Добавляет API ID и API HASH в BuildVars.java"""
    try:
        bv = find_file("BuildVars.java")
        if not bv: print("⚠ BuildVars.java не найден"); return errors
        text = read(bv)
        
        if API_ID in text:
            print("↩ skip BuildVars (API уже установлены)"); return errors
        
        # Ищем строки где задаются значения и заменяем их
        patterns = [
            (r'public static final int APP_ID\s*=\s*\d+\s*;', 'public static final int APP_ID = ' + API_ID + ';'),
            (r'public static final String APP_HASH\s*=\s*"[^"]*"\s*;', 'public static final String APP_HASH = "' + API_HASH + '";'),
            (r'APP_ID\s*=\s*\d+\s*;', 'APP_ID = ' + API_ID + ';'),
            (r'APP_HASH\s*=\s*"[^"]*"\s*;', 'APP_HASH = "' + API_HASH + '";'),
        ]
        
        modified = False
        for pattern, replacement in patterns:
            new_text = re_mod.sub(pattern, replacement, text, count=1)
            if new_text != text:
                text = new_text
                modified = True
                print(f"✔ BuildVars: updated API credentials")
        
        if modified:
            write(bv, text)
    except Exception as e:
        print(f"⚠ BuildVars patch failed: {e}")
    
    return errors


def main():
    print("▶ WeryGram patcher\n")
    print(f"📱 API ID: {API_ID}")
    print(f"📱 API HASH: {API_HASH}\n")
    errors = 0

    errors = patch_user_config(errors)
    errors = patch_messages_controller(errors)
    errors = patch_stars_controller(errors)
    errors = patch_app_name(errors)
    errors = patch_drawer_layout(errors)
    errors = patch_api_credentials(errors)

    sa = find_file("SettingsActivity.java")
    if not sa: print("✘ SettingsActivity.java not found", file=sys.stderr); sys.exit(1)

    if not insert_before(sa, "import org.telegram.ui.Components.",
                         "import org.telegram.ui.WeryGramPremiumActivity;"): errors += 1

    text = read(sa)
    
    if 'SettingCell.Factory.of(1000' not in text:
        account_button_marker = 'items.add(SettingCell.Factory.of(1, IconBackgroundColors.BLUE.top, IconBackgroundColors.BLUE.bottom, R.drawable.settings_account'
        
        if account_button_marker in text:
            wery_button = 'items.add(SettingCell.Factory.of(1000, 0xFF9C27B0, 0xFF7B1FA2, R.drawable.msg_settings, "WeryGram"));\n        '
            text = text.replace('items.add(SettingCell.Factory.of(1,', wery_button + 'items.add(SettingCell.Factory.of(1,', 1)
            print("✔ WeryGram button added")
        else:
            print("✘ Could not find Account button marker", file=sys.stderr); errors += 1
    else:
        print("↩ WeryGram button already exists")

    if 'case 1000:' not in text:
        case_marker = 'case 1:\n                presentFragment(new UserInfoActivity());'
        
        if case_marker in text:
            wery_case = 'case 1000:\n                presentFragment(new WeryGramPremiumActivity());\n                break;\n            case 1:\n                presentFragment(new UserInfoActivity());'
            text = text.replace(case_marker, wery_case, 1)
            print("✔ WeryGram click handler added")
        else:
            print("⚠ Could not find click handler marker", file=sys.stderr)
    else:
        print("↩ WeryGram handler already exists")

    write(sa, text)

    ui_dir = os.path.dirname(sa)
    for fname, content in [
        ("WeryGramPremiumActivity.java", ACTIVITY),
        ("WeryGramGifts.java",           GIFTS_JAVA),
    ]:
        dest = os.path.join(ui_dir, fname)
        if os.path.exists(dest): os.remove(dest)
        with open(dest, "w", encoding="utf-8") as f: f.write(content)
        print(f"✔ created {fname}")

    if errors > 0:
        print(f"\n✘ {errors} ошибок", file=sys.stderr); sys.exit(1)
    print("\n✅ Done.")

if __name__ == "__main__":
    main()
