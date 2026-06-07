import { Stack, usePathname } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { View, Platform } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";

import { useIconFonts } from "@/src/hooks/use-icon-fonts";
import { AuthProvider } from "@/src/context/AuthContext";
import { trackPageview } from "@/src/utils/track";
import { WebNav, BrandGlow } from "@/src/components/WebNav";
import { WebFooter } from "@/src/components/WebFooter";

// Keep the native splash visible from cold start until icon fonts register.
// Required because @expo/vector-icons' componentDidMount fallback fires
// Font.loadAsync against a broken vendor path if any <Icon> mounts before
// the family is registered — which throws on Android Expo Go.
SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [loaded, error] = useIconFonts();
  const pathname = usePathname();

  useEffect(() => {
    if (loaded || error) {
      SplashScreen.hideAsync();
    }
  }, [loaded, error]);

  useEffect(() => {
    if (pathname) trackPageview(pathname);
  }, [pathname]);

  if (!loaded && !error) return null;

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <StatusBar style="light" />
        <View style={{ flex: 1, backgroundColor: "#0A0413" }}>
          {Platform.OS === "web" && <WebNav />}
          {Platform.OS === "web" && <BrandGlow />}
          <View style={{ flex: 1 }}>
            <Stack
              screenOptions={{
                headerShown: false,
                contentStyle: { backgroundColor: "transparent" },
                animation: "fade",
              }}
            />
          </View>
          {Platform.OS === "web" && <WebFooter />}
        </View>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
