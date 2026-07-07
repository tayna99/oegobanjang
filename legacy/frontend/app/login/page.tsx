import { Suspense } from "react";

import { OperatorLoginPage } from "../../features/auth/OperatorLoginPage";

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <OperatorLoginPage />
    </Suspense>
  );
}
