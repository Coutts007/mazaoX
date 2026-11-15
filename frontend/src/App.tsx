import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { RequireAuth } from "./auth/RequireAuth";
import Audit from "./pages/admin/Audit";
import AdminIssues from "./pages/admin/Issues";
import AdminListings from "./pages/admin/Listings";
import Overview from "./pages/admin/Overview";
import AdminReviews from "./pages/admin/Reviews";
import Users from "./pages/admin/Users";
import Browse from "./pages/Browse";
import FarmDashboard from "./pages/farm/Dashboard";
import DemandMarket from "./pages/farm/DemandMarket";
import ListingEditor from "./pages/farm/ListingEditor";
import MyListings from "./pages/farm/MyListings";
import MyReviews from "./pages/farm/MyReviews";
import Cart from "./pages/Cart";
import Home from "./pages/Home";
import ListingDetail from "./pages/ListingDetail";
import Notifications from "./pages/Notifications";
import OrderDetail from "./pages/OrderDetail";
import Orders from "./pages/Orders";
import Profile from "./pages/Profile";
import Requests from "./pages/Requests";
import Login from "./pages/Login";
import { Forbidden, NotFound } from "./pages/NotFound";
import Register from "./pages/Register";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="browse" element={<Browse />} />
        <Route path="listings/:id" element={<ListingDetail />} />
        <Route path="cart" element={<Cart />} />
        <Route path="orders" element={<RequireAuth roles={["buyer"]}><Orders /></RequireAuth>} />
        <Route path="orders/:id" element={<RequireAuth><OrderDetail /></RequireAuth>} />
        <Route path="requests" element={<RequireAuth roles={["buyer"]}><Requests /></RequireAuth>} />
        <Route path="notifications" element={<RequireAuth><Notifications /></RequireAuth>} />
        <Route path="me" element={<RequireAuth><Profile /></RequireAuth>} />
        <Route path="farm" element={<RequireAuth roles={["farmer"]}><FarmDashboard /></RequireAuth>} />
        <Route path="farm/listings" element={<RequireAuth roles={["farmer"]}><MyListings /></RequireAuth>} />
        <Route path="farm/listings/new" element={<RequireAuth roles={["farmer"]}><ListingEditor /></RequireAuth>} />
        <Route path="farm/listings/:id" element={<RequireAuth roles={["farmer"]}><ListingEditor /></RequireAuth>} />
        <Route path="farm/orders" element={<RequireAuth roles={["farmer"]}><Orders /></RequireAuth>} />
        <Route path="farm/demand" element={<RequireAuth roles={["farmer"]}><DemandMarket /></RequireAuth>} />
        <Route path="farm/reviews" element={<RequireAuth roles={["farmer"]}><MyReviews /></RequireAuth>} />
        <Route path="admin" element={<RequireAuth roles={["admin"]}><Overview /></RequireAuth>} />
        <Route path="admin/users" element={<RequireAuth roles={["admin"]}><Users /></RequireAuth>} />
        <Route path="admin/listings" element={<RequireAuth roles={["admin"]}><AdminListings /></RequireAuth>} />
        <Route path="admin/orders" element={<RequireAuth roles={["admin"]}><Orders /></RequireAuth>} />
        <Route path="admin/issues" element={<RequireAuth roles={["admin"]}><AdminIssues /></RequireAuth>} />
        <Route path="admin/reviews" element={<RequireAuth roles={["admin"]}><AdminReviews /></RequireAuth>} />
        <Route path="admin/audit" element={<RequireAuth roles={["admin"]}><Audit /></RequireAuth>} />
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />
        <Route path="forbidden" element={<Forbidden />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
