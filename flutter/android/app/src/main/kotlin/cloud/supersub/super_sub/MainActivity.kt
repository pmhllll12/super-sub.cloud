package cloud.supersub.super_sub

import android.os.Bundle
import android.view.View
import android.view.WindowInsets
import android.view.WindowInsetsController
import io.flutter.embedding.android.FlutterActivity

/**
 * 🔴 **하단 내비게이션 바만 감춘다 — 상단 상태 바는 남긴다** (2026-09-22).
 *
 * Flutter 의 `SystemChrome.setEnabledSystemUIMode` 로는 이 조합이 안 나온다:
 *
 *  - `manual` + `overlays: [top]` — 하단만 감추지만, 쓸어 올리면 바가
 *    **자리를 차지해서** 화면 아래가 밀린다(사용자: 「버그 뭐야?」).
 *  - `immersiveSticky` — 겹쳐서 나왔다 저절로 사라지지만 **상태 바까지**
 *    같이 감춘다. 둘을 따로 못 고른다.
 *
 * 그래서 안드로이드 쪽에서 직접 잡는다. `BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE`
 * 가 바로 그 동작이다 — 쓸어 올리면 **화면 위에 겹쳐** 잠깐 나왔다가, 손을
 * 떼고 가만히 있으면 저절로 들어간다. 그동안 **레이아웃은 안 밀린다.**
 */
class MainActivity : FlutterActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        hideNavigationBar()
    }

    /**
     * 🔴 **창이 다시 앞에 설 때마다 도로 감춘다.** 앨범·카메라를 다녀오거나
     * 앱을 잠깐 나갔다 오면 시스템이 바를 되돌려 놓는다 — 다시 안 감추면
     * 하단 바가 그대로 남는다.
     */
    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideNavigationBar()
    }

    @Suppress("DEPRECATION")
    private fun hideNavigationBar() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
            window.insetsController?.let {
                it.systemBarsBehavior =
                    WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
                it.hide(WindowInsets.Type.navigationBars())
            }
        } else {
            // API 30 미만 — 같은 뜻의 옛 플래그. `IMMERSIVE_STICKY` 가
            // 「겹쳐서 잠깐 나왔다 저절로 사라진다」이고, `FULLSCREEN` 을
            // 안 넣었으므로 **상태 바는 그대로** 있다.
            window.decorView.systemUiVisibility =
                View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
                View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        }
    }
}
