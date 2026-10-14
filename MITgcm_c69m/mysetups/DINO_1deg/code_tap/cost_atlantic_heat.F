#include "COST_OPTIONS.h"

      subroutine cost_atlantic_heat( myThid )
C     /==========================================================\
C     | subroutine cost_atlantic_heat                            |
C     | o This routine computes the meridional heat transport.   |
C     |   The current indices are for North Atlantic 29N         |
C     |   2x2 global setup.                                      |
C     \==========================================================/
       implicit none

C     == Global variables ===
#include "SIZE.h"
#include "EEPARAMS.h"
#include "PARAMS.h"
#include "GRID.h"
#include "DYNVARS.h"
#include "cost.h"

C     ======== Routine arguments ======================
C     myThid - Thread number for this instance of the routine.
      integer myThid

#ifdef ALLOW_COST_ATLANTIC_HEAT
C     ========= Local variables =========================
      integer    isecbeg      , isecend      , jsec
      integer    jsecbeg      , jsecend      , isec
      integer    kmaxdepth
      integer i, j, k
      integer ig, jg
      integer bi, bj
      _RL     locfc
      _RL     uVel_bar(Nr), vVel_bar(Nr), theta_bar(Nr)
      _RL     thetaUvel_bar(Nr), thetaVvel_bar(Nr)
      _RL     countU(Nr), countV(Nr), countT(Nr)
      _RL     countTU(Nr), countTV(Nr)
      _RL     petawatt
      _RL     sum
      parameter( petawatt = 1. _d +15 )

C     adjust the following line of code to define the zonal section
C     where you are interested to calculated AMOC transport.
C     jsec is the (1-based) grid row whose SOUTHERN face carries the vVel
C     the section integrates; analyses/DINO_1deg/grid_and_cost_sections.ipynb
C     maps a latitude to a row.
C     jsec = 148 since 2026-10-13: the row of the overturning maximum of
C     the 200-year spin-up 31203 (row centre 43.2 N, face 42.8 N; psi peaks
C     there, 7.37 Sv at the 848 m interface, in every decade of the
C     spin-up), found by analyses/DINO_1deg/adjoint/kappa_v_ensemble_gmFwd/
C     overturning_maximum.py. Until then jsec = 127 (26.05 N), the section
C     of every adjoint run up to job 31434; a run's build_info.txt records
C     its section (cost_section_jsec=).
      parameter( isecbeg = 1, isecend = 51, jsec = 148 )
C     the following line defines a meridional section, but I am not using
C     it in the soma-adjoint setup. To confirm, search for
C     jsecbeg/jsecend in the compiled version of this file (.f file) in the build
C     directory: there should be only two instances of them
      parameter( jsecbeg = 1, jsecend = 62, isec = 30 )
#ifdef ALLOW_COST_ATLANTIC_HEAT_DOMASS
C     integrate only the upper 24 vertical levels (upper 848 m; see "delR"
C     in input_tap/data): the interface at which psi peaks on row jsec, so
C     the cost is the overturning maximum itself (since 2026-10-13; the
C     upper 25 levels, 982 m, until then, when the section was at 26 N and
C     psi was still rising at the cut)
      parameter ( kmaxdepth = 24 )
#else
      parameter ( kmaxdepth = 14 )
#endif

C------------------------------------------------------
C     Accumulate meridionally integrated transports
C     Note bar(V)*bar(T) not bar(VT)
C     Attention pYFaceA [m^2*gravity*rhoConst]
C------------------------------------------------------

      DO bj=myByLo(myThid),myByHi(myThid)
       DO bi=myBxLo(myThid),myBxHi(myThid)

        locfc = 0.0
        sum = 0.0

#define MERID_TRANSPORT

#ifdef MERID_TRANSPORT

#undef ENERGYNORM
#ifdef ENERGYNORM

        do i=1,sNx
         ig = myXGlobalLo-1+(bi-1)*sNx+i
         if ((ig .ge. isecbeg) .and. (ig .le. isecend)) then
          sum = 0.0
          do k = 1, kmaxdepth
           sum = sum
     &            + (vVel(i,j,k,bi,bj) * maskS(i,j,k,bi,bj)
     &            * drF(k))**2
          end do
          locfc = locfc + sum*dxG(i,j,bi,bj)
         end if
        end do

#else

        do j=1,sNy
         jg = myYGlobalLo-1+(bj-1)*sNy+j
         if (jg .eq. jsec) then

          do k = 1, Nr
           vVel_bar(k) = 0.0
           thetaVvel_bar(k) = 0.0
           countV(k) = 0.0
           countTV(k) = 0.0
           do i=1,sNx
            ig = myXGlobalLo-1+(bi-1)*sNx+i
c
            if ((ig .ge. isecbeg) .and. (ig .le. isecend)) then
               vVel_bar(k) = vVel_bar(k)
     &              + cMeanVVel(i,j,k,bi,bj)*dxG(i,j,bi,bj)
     &                 *maskS(i,j,k,bi,bj)

               thetaVvel_bar(k) = thetaVvel_bar(k)
     &            + cMeanThetaVVel(i,j,k,bi,bj)*dxG(i,j,bi,bj)
     &                 *maskS(i,j,k,bi,bj)*maskC(i,j,k,bi,bj)

             countTV(k) = countTV(k) +
     &            maskS(i,j,k,bi,bj)*maskC(i,j,k,bi,bj)
             countV(k) = countV(k) +
     &            maskS(i,j,k,bi,bj)
            end if

           enddo
          enddo
c
          do k = 1, Nr
#ifdef ALLOW_COST_ATLANTIC_HEAT_DOMASS
           if ( k .LE. kmaxdepth .AND. countV(k) .NE. 0) then
            sum = sum
     &            + vVel_bar(k)*drF(k)/countV(k)
           end if
#else
           if ( k .LE. kmaxdepth .AND. countTV(k) .NE. 0) then
            sum = sum
     &            + thetaVVel_bar(k)*drF(k)/countTV(k)
           end if
#endif
          end do

#endif /* ENERGYNORM */

#else

cph need to change this part to go from
cph \bar{u}*\bar{T} to \bar{u*T}
cph (required store dir. are now in place)

        do i=1,sNx
         ig = myXGlobalLo-1+(bi-1)*sNx+i
         if (ig .eq. isec) then

          do k = 1, Nr
           uVel_bar(k) = 0.0
           theta_bar(k) = 0.0
           countT(k) = 0.0
           countU(k) = 0.0
           do j=1,sNy
            jg = myYGlobalLo-1+(bj-1)*sNy+j
c
            if ((jg .ge. jsecbeg) .and. (jg .le. jsecend)) then
             uVel_bar(k) = uVel_bar(k)
     &                      + cMeanUVel(i,j,k,bi,bj)
     &                      *maskW(i,j,k,bi,bj)
     &                      *maskC(i,j,k,bi,bj)*maskC(i-1,j,k,bi,bj)
             theta_bar(k) = theta_bar(k) +
     &            0.5*( cMeanTheta(i,j,k,bi,bj)
     &                 +cMeanTheta(i-,j,k,bi,bj) )
     &                 *maskW(i,j,k,bi,bj)*dyG(i,j,bi,bj)
     &                 *maskC(i,j,k,bi,bj)*maskC(i-1,j,k,bi,bj)
             countT(k) = countT(k) + maskW(i,j,k,bi,bj)
     &                   *maskC(i,j,k,bi,bj)*maskC(i-1,j,k,bi,bj)
             countU(k) = countU(k) + maskW(i,j,k,bi,bj)
     &                   *maskC(i,j,k,bi,bj)*maskC(i-1,j,k,bi,bj)
            end if

           enddo
          enddo
c
          do k = 1, Nr
           if ( k .LE. kmaxdepth .AND.
     &          countT(k) .NE. 0 .AND. countU(k) .NE. 0) then
            sum = sum
     &            + uVel_bar(k) * theta_bar(k) * drF(k)
     &            / ( countT(k) * countU(k) )
           end if
          end do

#endif

         end if
        end do

#ifdef ALLOW_COST_ATLANTIC_HEAT_DOMASS
        objf_atl(bi,bj) =
     &     sum*1.E-6
#else
        objf_atl(bi,bj) =
     &     sum*HeatCapacity_Cp*rhoConst/petawatt
#endif

c--   end of bi,bj loop
       end do
      end do

#endif

      end
