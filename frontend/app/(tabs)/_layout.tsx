import { Tabs, Redirect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Platform, View, ActivityIndicator } from "react-native";
import { BlurView } from "expo-blur";
import { C } from "@/src/theme";
import { useAuth } from "@/src/context/AuthContext";

export default function TabsLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: C.bg, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator color={C.brand} />
      </View>
    );
  }
  if (!user) return <Redirect href="/onboarding" />;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: C.brand,
        tabBarInactiveTintColor: C.textMuted,
        tabBarStyle: {
          position: "absolute",
          backgroundColor: Platform.OS === "ios" ? "transparent" : "rgba(10,10,10,0.95)",
          borderTopColor: C.border,
          borderTopWidth: 1,
          height: 76,
          paddingTop: 8,
          paddingBottom: 16,
        },
        tabBarBackground: Platform.OS === "ios"
          ? () => <BlurView intensity={50} tint="dark" style={{ flex: 1 }} />
          : undefined,
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
      }}
    >
      <Tabs.Screen
        name="home"
        options={{
          title: "Home",
          tabBarButtonTestID: "tab-home",
          tabBarIcon: ({ color, size }) => <Ionicons name="home" size={size - 2} color={color} />,
        }}
      />
      <Tabs.Screen
        name="paths"
        options={{
          title: "Paths",
          tabBarButtonTestID: "tab-paths",
          tabBarIcon: ({ color, size }) => <Ionicons name="library" size={size - 2} color={color} />,
        }}
      />
      <Tabs.Screen
        name="tutor"
        options={{
          title: "AI Tutor",
          tabBarButtonTestID: "tab-tutor",
          tabBarIcon: ({ color, size }) => <Ionicons name="sparkles" size={size - 2} color={color} />,
        }}
      />
      <Tabs.Screen
        name="models"
        options={{
          title: "Models",
          tabBarButtonTestID: "tab-models",
          tabBarIcon: ({ color, size }) => <Ionicons name="planet" size={size - 2} color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarButtonTestID: "tab-profile",
          tabBarIcon: ({ color, size }) => <Ionicons name="person-circle" size={size - 2} color={color} />,
        }}
      />
    </Tabs>
  );
}
