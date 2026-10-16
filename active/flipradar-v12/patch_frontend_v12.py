"""Apply minimal V12 compatibility edits to ORIGINAL TSX, preserving all styling."""
from pathlib import Path
import sys

def replace_once(path, old, new):
    p=Path(path);s=p.read_text(encoding='utf-8')
    if s.count(old)!=1:
        raise SystemExit(f'UNEXPECTED SOURCE {p}: expected once, found {s.count(old)} for {old[:60]!r}')
    p.write_text(s.replace(old,new),encoding='utf-8')

def main(mobile):
    root=Path(mobile)/'src'
    config=root/'utils/config.ts'
    replace_once(config,
      "  return (process.env.EXPO_PUBLIC_FLIP_API_URL ?? '').replace(/\\/$/, '');",
      "  const base = (process.env.EXPO_PUBLIC_FLIP_API_URL ?? '').replace(/\\/$/, '');\n  if (base === 'same-origin' && Platform.OS === 'web') return globalThis.location?.origin ?? '';\n  return base;")
    replace_once(config,
      "  const base = apiBaseUrl();\n  if (!base) {",
      "  const base = apiBaseUrl();\n  if (process.env.EXPO_PUBLIC_FLIP_API_URL === 'same-origin' && Platform.OS === 'web') return Boolean(base);\n  if (!base) {")
    auth=root/'api/endpoints/auth.ts'
    replace_once(auth,
      'export async function register(\n  username: string,\n  password: string,\n): Promise<void> {',
      'export async function register(\n  username: string,\n  email: string,\n  password: string,\n): Promise<void> {')
    replace_once(auth,
      'body: JSON.stringify({ username, password }),\n  });\n  await saveTokens(tokens);\n}\n\nexport async function fetchMe',
      'body: JSON.stringify({ username, email, password }),\n  });\n  await saveTokens(tokens);\n}\n\nexport async function fetchMe')
    context=root/'features/auth/AuthContext.tsx'
    replace_once(context,
      '  register: (username: string, password: string) => Promise<void>;',
      '  register: (username: string, email: string, password: string) => Promise<void>;')
    replace_once(context,
      '    async (username: string, password: string) => {\n      if (mode !== "live")',
      '    async (username: string, email: string, password: string) => {\n      if (mode !== "live")')
    replace_once(context,
      '      await registerAccount(username.trim(), password);',
      '      await registerAccount(username.trim(), email.trim(), password);')
    portal=root/'features/portal/PortalPage.web.tsx'
    replace_once(portal,
      '  updateMemberAccess,\n} from "@/api/endpoints/portal";',
      '  updateMemberAccess,\n  deleteMemberAccount,\n} from "@/api/endpoints/portal";')
    replace_once(portal,
      '  const [username, setUsername] = useState("");\n  const [password, setPassword] = useState("");',
      '  const [username, setUsername] = useState("");\n  const [email, setEmail] = useState("");\n  const [password, setPassword] = useState("");')
    replace_once(portal,
      '      if (register) await auth.register(username, password);',
      '      if (register) await auth.register(username, email, password);')
    replace_once(portal,
      '          Login\n          <input',
      '          {register ? "Login" : "Adres e-mail (administrator: login)"}\n          <input')
    replace_once(portal,
      '            maxLength={60}\n            pattern={register ? "[a-zA-Z0-9][a-zA-Z0-9_.-]{2,59}" : undefined}',
      '            maxLength={register ? 32 : 200}\n            pattern={register ? "[a-zA-Z][a-zA-Z0-9_.-]{2,31}" : undefined}')
    replace_once(portal,
      '            placeholder="Twój login"\n            required\n          />\n        </label>\n        <label className="fr-field">\n          Hasło',
      '            placeholder={register ? "Wybierz login" : "E-mail lub login administratora"}\n            required\n          />\n        </label>\n        {register ? (\n          <label className="fr-field">\n            Adres e-mail — wymagany\n            <input type="email" name="email" autoComplete="email" value={email}\n              onChange={(e) => setEmail(e.target.value)} maxLength={200} required\n              placeholder="twoj@email.pl" />\n          </label>\n        ) : null}\n        <label className="fr-field">\n          Hasło')
    searchpage=root/'app/searches/index.tsx'
    replace_once(searchpage,
      """  const [platforms, setPlatforms] = useState<SearchPlatform[]>([
    ...searchPlatforms,
  ]);""",
      """  const [platforms, setPlatforms] = useState<SearchPlatform[]>([
    "OLX",
  ]);""")
    replace_once(searchpage,
      """        <DemoBanner />
        <View""",
      """        <DemoBanner />
        {mode === "live" ? (
          <WorkspaceNotice text="Aktualny skaner obsługuje indywidualne wyszukiwania OLX. Fraza, kategoria i limit ceny działają. Koszty, ROI i prognoza zysku nie filtrują jeszcze skanera V9." />
        ) : null}
        <View""")
    # New delete action in original React account admin panel; this is the
    # only new admin control, all existing styles/components stay intact.
    replace_once(portal,
      '  const commit = async () => {\n    if (!pending) return;',
      '''  const deleteMember = async (userId: string, username: string) => {
    const confirm = window.prompt(`Usunięcie konta ${username} jest nieodwracalne. Wpisz dokładnie login:`);
    if (confirm !== username) return;
    setBusy(true);
    setError("");
    try {
      await deleteMemberAccount(userId, confirm);
      await cache.invalidateQueries({ queryKey: ["portal-admin"] });
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally { setBusy(false); }
  };
  const commit = async () => {
    if (!pending) return;''')
    replace_once(portal,
      '                  >\n                    Wstrzymaj\n                  </button>',
      '''                  >
                    Wstrzymaj
                  </button>
                  <button className="fr-btn fr-btn-small fr-btn-danger"
                    disabled={busy} onClick={() => {void deleteMember(member.user_id,member.username);}}>
                    Usuń konto
                  </button>''')
    replace_once(portal,
      '      {!data.data.accounts.some((member) => member.role !== "OWNER") ? (',
      '''      <p className="fr-plans-note">Dodatkowe ustawienia ról i platform:
        {" "}<a href="/admin/uzytkownicy?legacy=1">zarządzanie zaawansowane</a>.
      </p>
      {!data.data.accounts.some((member) => member.role !== "OWNER") ? (''')
    endpoints=root/'api/endpoints/portal.ts'
    endpoints.write_text(endpoints.read_text(encoding='utf-8')+'''
/** Deletes a V10 account and its own private data. Owner/admin only. */
export function deleteMemberAccount(userId: string, confirm: string) {
  return apiRequest<{ok: boolean}>("/api/v1/portal/admin/delete", {
    method: "POST", body: JSON.stringify({ user_id: userId, confirm }),
  });
}
''',encoding='utf-8')
    print('PASS: original Expo/React UI patched for V10 email auth and admin delete')

if __name__=='__main__':main(sys.argv[1])
