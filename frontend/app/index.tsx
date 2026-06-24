import { useEffect } from "react";
import { Platform, View, ActivityIndicator } from "react-native";
import { Redirect } from "expo-router";
import { useAuth } from "@/src/context/AuthContext";
import { C } from "@/src/theme";

export default function Index() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: C.bg, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator color={C.brand} size="large" />
      </View>
    );
  }

  // Web is the primary surface — public visitors land at /landing, authed users go to dashboard.
  // (Native mobile path retained as a fallback but not the priority for this phase.)
  if (Platform.OS === "web") {
    if (!user) return <Redirect href="/landing" />;
    return <Redirect href="/(tabs)/home" />;
  }
  if (!user) {
    return <Redirect href="/onboarding" />;
  }
  return <Redirect href="/(tabs)/home" />;
}
