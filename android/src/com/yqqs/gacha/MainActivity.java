package com.yqqs.gacha;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * 元气骑士扭蛋机 —— 全部内容来自打包在 assets/ 里的静态网页，
 * 因此这里只需要一个最朴素的 WebView 容器：不联网、不申请任何权限。
 */
public class MainActivity extends Activity {

    private static final String PAGE = "file:///android_asset/index.html";

    private WebView webView;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Window window = getWindow();
        window.setStatusBarColor(Color.parseColor("#0B1020"));
        window.setNavigationBarColor(Color.parseColor("#0B1020"));

        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#0B1020"));
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(false);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setTextZoom(100);
        settings.setDefaultTextEncodingName("utf-8");

        // 页面是纯离线单页，禁止任何外部跳转，保持"抽卡"这一件事。
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return true;
            }
        });

        setContentView(webView);
        webView.loadUrl(PAGE);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) {
            webView.onResume();
        }
    }

    @Override
    protected void onPause() {
        if (webView != null) {
            webView.onPause();
        }
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.setVisibility(View.GONE);
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
